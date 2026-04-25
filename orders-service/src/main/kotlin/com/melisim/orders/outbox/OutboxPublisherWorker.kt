package com.melisim.orders.outbox

import io.micrometer.core.instrument.MeterRegistry
import io.micrometer.core.instrument.Tag
import io.micrometer.core.instrument.Timer
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.annotation.Value
import org.springframework.data.domain.PageRequest
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.scheduling.annotation.EnableScheduling
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Component
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

@Component
@EnableScheduling
class OutboxPublisherWorker(
    private val repository: OutboxRepository,
    private val kafka: KafkaTemplate<String, String>,
    private val meterRegistry: MeterRegistry,
    @Value("\${melisim.outbox.batch-size:50}") private val batchSize: Int,
    @Value("\${melisim.outbox.max-attempts:10}") private val maxAttempts: Int,
    @Value("\${melisim.outbox.send-timeout-seconds:10}") private val sendTimeoutSeconds: Long,
) {
    private val log = LoggerFactory.getLogger(javaClass)
    private val pendingGauge = AtomicInteger(0)

    init {
        meterRegistry.gauge(
            "melisim_outbox_events",
            mutableListOf(Tag.of("state", "pending")),
            pendingGauge,
        ) { it.get().toDouble() }
    }

    /**
     * Drains a batch of PENDING outbox rows. Sends are PIPELINED — we fire all
     * KafkaTemplate.send() calls first (each returns a future), then await each
     * one. Combined with producer-side batching (linger.ms + batch.size), this
     * lets a single drain shovel many events out the door in a single round-trip
     * to the broker, instead of one round-trip per event.
     *
     * Concurrent workers are safe: the SELECT uses PESSIMISTIC_WRITE, so other
     * instances skip the rows we're holding.
     */
    @Scheduled(fixedDelayString = "\${melisim.outbox.poll-interval-ms:2000}")
    @Transactional
    fun drain() {
        val batch = repository.lockPending(PageRequest.of(0, batchSize))
        pendingGauge.set(batch.size)
        if (batch.isEmpty()) return

        val sample = Timer.start(meterRegistry)
        val pendingSends = batch.map { event ->
            // Fire all sends in parallel — Kafka producer pipelines internally.
            event to kafka.send(event.topic, event.aggregateId.toString(), event.payload)
        }

        var sent = 0
        var failed = 0
        pendingSends.forEach { (event, future) ->
            try {
                future.get(sendTimeoutSeconds, TimeUnit.SECONDS)
                event.status = OutboxStatus.SENT
                event.sentAt = Instant.now()
                meterRegistry.counter(
                    "melisim_events_published_total",
                    "event_type", event.eventType,
                ).increment()
                sent++
            } catch (e: Exception) {
                event.attempts += 1
                event.lastError = e.message?.take(500)
                if (event.attempts >= maxAttempts) {
                    event.status = OutboxStatus.FAILED
                    log.error(
                        "outbox giving up id={} type={} after {} attempts: {}",
                        event.id, event.eventType, event.attempts, e.message,
                    )
                } else {
                    log.warn(
                        "outbox publish failed id={} type={} attempt={} err={}",
                        event.id, event.eventType, event.attempts, e.message,
                    )
                }
                failed++
            }
        }
        sample.stop(meterRegistry.timer("melisim_outbox_drain_seconds"))

        if (sent > 0 || failed > 0) {
            log.info("outbox drain: sent={} failed={} batch={}", sent, failed, batch.size)
        }
    }
}
