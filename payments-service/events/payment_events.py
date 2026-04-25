import json
import logging
import os

from aiokafka import AIOKafkaProducer

log = logging.getLogger("payments.events")


class KafkaPublisher:
    def __init__(self, brokers: str | None = None) -> None:
        self.brokers = brokers or os.getenv("KAFKA_BROKERS", "localhost:9092")
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        try:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.brokers)
            await self._producer.start()
            log.info("kafka producer started on %s", self.brokers)
        except Exception as e:
            log.warning("could not start kafka producer: %s", e)
            self._producer = None

    async def stop(self) -> None:
        if self._producer is not None:
            try:
                await self._producer.stop()
            except Exception:
                pass

    async def publish(self, topic: str, key: str, value: dict) -> None:
        if self._producer is None:
            log.warning("kafka unavailable; dropping event topic=%s", topic)
            return
        try:
            await self._producer.send_and_wait(
                topic,
                key=key.encode("utf-8"),
                value=json.dumps(value, default=str).encode("utf-8"),
            )
        except Exception as e:
            log.warning("kafka publish failed topic=%s: %s", topic, e)


publisher = KafkaPublisher()
