#!/bin/bash
set -e

KAFKA_BROKER="${KAFKA_BROKER:-kafka:9092}"

echo "Waiting for Kafka at $KAFKA_BROKER..."
until kafka-topics --bootstrap-server "$KAFKA_BROKER" --list >/dev/null 2>&1; do
  sleep 2
done

TOPICS=(
  "order-created"
  "payment-confirmed"
  "payment-failed"
  "stock-updates"
  "stock-alert"
  "product-created"
)

for topic in "${TOPICS[@]}"; do
  kafka-topics --bootstrap-server "$KAFKA_BROKER" \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions 3 \
    --replication-factor 1
  echo "Topic ensured: $topic"
done

echo "All MeliSim Kafka topics ready."
