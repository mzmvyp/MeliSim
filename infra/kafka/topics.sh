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

# DLQ topics get 1 partition (human triage, not throughput) and a longer retention.
# Keep in sync with every consumer that publishes to <topic>.dlq:
#   notifications-service → order-created, payment-*, stock-alert
#   search-service        → product-created, stock-updates
DLQ_TOPICS=(
  "order-created.dlq"
  "payment-confirmed.dlq"
  "payment-failed.dlq"
  "stock-alert.dlq"
  "product-created.dlq"
  "stock-updates.dlq"
)

for topic in "${TOPICS[@]}"; do
  kafka-topics --bootstrap-server "$KAFKA_BROKER" \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions 3 \
    --replication-factor 1
  echo "Topic ensured: $topic"
done

for topic in "${DLQ_TOPICS[@]}"; do
  kafka-topics --bootstrap-server "$KAFKA_BROKER" \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions 1 \
    --replication-factor 1 \
    --config retention.ms=2592000000   # 30 days
  echo "DLQ topic ensured: $topic"
done

echo "All MeliSim Kafka topics ready."
