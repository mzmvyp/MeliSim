import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy.ext.asyncio import async_sessionmaker

from services import notification_service

log = logging.getLogger("notifications.consumer")

TOPIC_HANDLERS: dict[str, Callable[[object, dict], Awaitable[None]]] = {
    "order-created":      notification_service.dispatch_order_created,
    "payment-confirmed":  notification_service.dispatch_payment_confirmed,
    "payment-failed":     notification_service.dispatch_payment_failed,
    "stock-alert":        notification_service.dispatch_stock_alert,
}

# Per-message retries inside the consumer loop. Beyond this, the message lands
# on the DLQ — operator inspects, fixes, and (optionally) replays.
MAX_RETRIES = int(os.getenv("CONSUMER_MAX_RETRIES", "3"))
DLQ_SUFFIX = ".dlq"


async def _publish_dlq(producer: AIOKafkaProducer, original_topic: str, msg, err: Exception) -> None:
    """
    Wrap the original payload + the failure reason and ship to <topic>.dlq.
    The DLQ is the explicit pressure-release valve: poison messages do NOT
    block the live partition (which is what happens if you retry forever).
    """
    dlq_topic = f"{original_topic}{DLQ_SUFFIX}"
    envelope = {
        "original_topic": original_topic,
        "original_partition": msg.partition,
        "original_offset": msg.offset,
        "original_key": (msg.key or b"").decode("utf-8", errors="replace"),
        "original_value": msg.value.decode("utf-8", errors="replace"),
        "error": str(err),
        "error_type": type(err).__name__,
        "failed_at": datetime.now(UTC).isoformat(),
    }
    try:
        await producer.send_and_wait(
            dlq_topic,
            key=(msg.key or b""),
            value=json.dumps(envelope).encode(),
        )
        log.error("DLQ topic=%s offset=%s: %s", original_topic, msg.offset, err)
    except Exception as e:
        # If the DLQ itself is down, we have to drop and log loudly — better
        # than blocking the consumer thread for every poison message.
        log.critical("DLQ publish failed topic=%s: %s (original error: %s)", dlq_topic, e, err)


async def _handle_with_retry(
    session_factory: async_sessionmaker,
    handler: Callable[[object, dict], Awaitable[None]],
    payload: dict,
    topic: str,
) -> Exception | None:
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session_factory() as session:
                await handler(session, payload)
            return None
        except Exception as e:
            last_err = e
            backoff_ms = min(200 * (2 ** (attempt - 1)), 2000)
            log.warning(
                "handler failed topic=%s attempt=%d err=%s; retrying in %dms",
                topic, attempt, e, backoff_ms,
            )
            await asyncio.sleep(backoff_ms / 1000)
    return last_err


async def run_consumer(session_factory: async_sessionmaker, stop_event: asyncio.Event) -> None:
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    topics = list(TOPIC_HANDLERS.keys())

    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=brokers,
        group_id="notifications-service",
        auto_offset_reset="earliest",
        enable_auto_commit=False,                 # commit explicitly after handling
        max_poll_records=100,
        partition_assignment_strategy=("cooperative-sticky",),
    )

    dlq_producer = AIOKafkaProducer(bootstrap_servers=brokers, acks="all", enable_idempotence=True)

    try:
        await consumer.start()
        await dlq_producer.start()
    except Exception as e:
        log.warning("kafka unavailable; consumer won't run: %s", e)
        return

    log.info("kafka consumer subscribed to: %s", topics)
    try:
        while not stop_event.is_set():
            try:
                batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=2)
            except TimeoutError:
                continue

            for tp, messages in batch.items():
                handler = TOPIC_HANDLERS.get(tp.topic)
                if handler is None:
                    continue
                for msg in messages:
                    try:
                        payload = json.loads(msg.value.decode("utf-8"))
                    except Exception as e:
                        await _publish_dlq(dlq_producer, tp.topic, msg, e)
                        continue
                    err = await _handle_with_retry(session_factory, handler, payload, tp.topic)
                    if err is not None:
                        await _publish_dlq(dlq_producer, tp.topic, msg, err)
                # Commit after the partition's batch — at-least-once delivery.
                await consumer.commit({tp: messages[-1].offset + 1})
    finally:
        try:
            await consumer.stop()
        finally:
            await dlq_producer.stop()
        log.info("kafka consumer stopped")
