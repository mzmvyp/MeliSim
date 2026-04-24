import asyncio
import json
import logging
import os

from aiokafka import AIOKafkaConsumer

from services.search_service import service

log = logging.getLogger("search.consumer")


async def run_consumer(stop_event: asyncio.Event) -> None:
    brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")
    consumer = AIOKafkaConsumer(
        "product-created",
        "stock-updates",
        bootstrap_servers=brokers,
        group_id="search-service",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    try:
        await consumer.start()
    except Exception as e:
        log.warning("kafka unavailable; consumer won't run: %s", e)
        return

    log.info("search consumer started")
    try:
        while not stop_event.is_set():
            try:
                batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=2)
            except asyncio.TimeoutError:
                continue
            for tp, messages in batch.items():
                for msg in messages:
                    try:
                        payload = json.loads(msg.value.decode("utf-8"))
                    except Exception:
                        continue
                    if tp.topic == "product-created":
                        product = payload.get("product", payload)
                        await service.index_product(product)
                    elif tp.topic == "stock-updates":
                        pid = payload.get("product_id")
                        if pid is not None:
                            await service.client.update(
                                index="products",
                                id=str(pid),
                                body={"doc": {"stock": payload.get("stock", 0)}},
                                refresh="wait_for",
                            )
    finally:
        await consumer.stop()
