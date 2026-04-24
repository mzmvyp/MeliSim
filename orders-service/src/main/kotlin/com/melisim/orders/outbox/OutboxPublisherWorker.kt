package com.melisim.orders.outbox

import io.micrometer.core.instrument.MeterRegistry
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.data.domain.PageRequest
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.scheduling.annotation.EnableScheduling
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Component
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.util.concurrent.atomic.AtomicInteger

@Component
@EnableScheduling
class OutboxPublisherWorker(
    private val repository: OutboxRepository,
    private val kafka: KafkaTemplate<String, String>,
    private val meterRegistry: MeterRegistry,
    @Value("\${melisim.outbox.batch-size:50}") private val batchSize: Int,
) {
    private val log = LoggerFactory.getLogger(javaClass)
    private val pendingGauge = AtomicInteger(0)

    init {
        meterRegistry.gauge("melisim_outbox_events", mutableListOf(io.micrometer.core.instrument.Tag.of("state", "pending")), pendingGauge) { it.get().toDouble() }
    }

    @Scheduled(fixedDelayString = "\${melisim.outbox.poll-interval-ms:2000}")
    @Transactional
    fun drain() {
        val batch = repository.lockPending(PageRequest.of(0, batchSize))
        pendingGauge.set(batch.size)
        if (batch.isEmpty()) return

        batch.forEach { event ->
            try {
                kafka.send(event.topic, event.aggregateId.toString(), event.payload).get()
                event.status = OutboxStatus.SENT
                event.sentAt = Instant.now()
                meterRegistry.counter("melisim_events_published_total", "event_type", event.eventType).increment()
                log.info("outbox shipped id={} type={} topic={}", event.id, event.eventType, event.topic)
            } catch (e: Exception) {
                event.attempts += 1
                event.lastError = e.message?.take(500)
                if (event.attempts >= 10) {
                    event.status = OutboxStatus.FAILED
                    log.error("outbox giving up id={} after {} attempts", event.id, event.attempts)
                } else {
                    log.warn("outbox publish failed id={} attempt={} err={}", event.id, event.attempts, e.message)
                }
            }
        }
        // JPA flushes on tx commit, so the updated statuses are persisted atomically.
    }
}
