-- Transactional Outbox pattern: order-created events are written to this table
-- inside the same DB transaction that persists the order row. A separate worker
-- (OutboxPublisherWorker) polls PENDING rows, ships them to Kafka, and marks
-- them SENT. This removes the dual-write hazard where the DB commits but the
-- Kafka publish fails (or vice versa), which was the previous implementation.
CREATE TABLE IF NOT EXISTS outbox_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    aggregate_type VARCHAR(60) NOT NULL,
    aggregate_id   BIGINT NOT NULL,
    event_type     VARCHAR(60) NOT NULL,
    topic          VARCHAR(120) NOT NULL,
    payload        JSON NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    attempts       INT NOT NULL DEFAULT 0,
    last_error     TEXT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at        TIMESTAMP NULL,
    INDEX idx_outbox_status_created (status, created_at),
    INDEX idx_outbox_aggregate (aggregate_type, aggregate_id)
) ENGINE=InnoDB;
