import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from services.search_service import service

log = logging.getLogger("search.consumer")

MAX_RETRIES = int(os.getenv("CONSUMER_MAX_RETRIES", "3"))
DLQ_SUFFIX = ".dlq"


async def _publish_dlq(producer: AIOKafkaProducer, original_topic: str, msg, err: Exception) -> None:
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
        log.critical("DLQ publish failed topic=%s: %s (original error: %s)", dlq_topic, e, err)


async def _handle_product_created(payload: dict) -> None:
    product = payload.get("product", payload)
    await service.index_product(product, strict=True)


async def _handle_stock_updates(payload: dict) -> None:
    pid = payload.get("product_id")
    if pid is None:
        raise ValueError("stock-updates payload missing product_id")
    stock = int(payload.get("stock", 0))
    await service.update_product_stock(int(pid), stock, strict=True)


TOPIC_HANDLERS: dict[str, Callable[[dict], Awaitable[None]]] = {
    "product-created": _handle_product_created,
    "stock-updates": _handle_stock_updates,
}


async def _handle_with_retry(handler: Callable[[dict], Awaitable[None]], payload: dict, topic: str) -> Exception | None:
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await handler(payload)
            return None
        except Exception as e:
            last_err = e
            backoff_ms = min(200 * (2 ** (attempt - 1)), 2000)
            log.warning(
                "handler failed topic=%s attempt=%d err=%s; retrying in %dms",
                topic,
                attempt,
                e,
                backoff_ms,
            )
            await asyncio.sleep(backoff_ms / 1000)
    return last_err


async def run_consumer(stop_event: asyncio.Event) -> None:
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    topics = list(TOPIC_HANDLERS.keys())

    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=brokers,
        group_id="search-service",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
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

    log.info("search consumer subscribed to: %s", topics)
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
                    err = await _handle_with_retry(handler, payload, tp.topic)
                    if err is not None:
                        await _publish_dlq(dlq_producer, tp.topic, msg, err)
                await consumer.commit({tp: messages[-1].offset + 1})
    finally:
        try:
            await consumer.stop()
        finally:
            await dlq_producer.stop()
        log.info("search consumer stopped")
