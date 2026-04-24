import asyncio
import json
import logging
import os
from typing import Callable, Awaitable

from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import async_sessionmaker

from services import notification_service

log = logging.getLogger("notifications.consumer")

TOPIC_HANDLERS: dict[str, Callable[[object, dict], Awaitable[None]]] = {
    "order-created":      notification_service.dispatch_order_created,
    "payment-confirmed":  notification_service.dispatch_payment_confirmed,
    "payment-failed":     notification_service.dispatch_payment_failed,
    "stock-alert":        notification_service.dispatch_stock_alert,
}


async def run_consumer(session_factory: async_sessionmaker, stop_event: asyncio.Event) -> None:
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    topics = list(TOPIC_HANDLERS.keys())

    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=brokers,
        group_id="notifications-service",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    try:
        await consumer.start()
    except Exception as e:
        log.warning("kafka unavailable; consumer won't run: %s", e)
        return

    log.info("kafka consumer subscribed to: %s", topics)
    try:
        while not stop_event.is_set():
            try:
                batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=2)
            except asyncio.TimeoutError:
                continue
            for tp, messages in batch.items():
                handler = TOPIC_HANDLERS.get(tp.topic)
                if handler is None:
                    continue
                for msg in messages:
                    try:
                        payload = json.loads(msg.value.decode("utf-8"))
                    except Exception:
                        log.warning("invalid JSON on topic=%s", tp.topic)
                        continue
                    async with session_factory() as session:
                        try:
                            await handler(session, payload)
                        except Exception as e:
                            log.error("handler failed topic=%s: %s", tp.topic, e)
    finally:
        await consumer.stop()
        log.info("kafka consumer stopped")
