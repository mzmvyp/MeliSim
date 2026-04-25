package com.melisim.orders.outbox

import org.slf4j.LoggerFactory
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Component
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * Periodic GC for the outbox table — without this, every published event lives
 * forever and the table grows unbounded.
 *
 * - Only SENT rows are deleted; FAILED stay for inspection / manual replay.
 * - Runs nightly. Tunable retention via `melisim.outbox.retention-days` (default 7d).
 */
@Component
class OutboxCleanupWorker(
    private val repository: OutboxRepository,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    @Scheduled(cron = "\${melisim.outbox.cleanup-cron:0 0 3 * * *}")
    @Transactional
    fun cleanup() {
        val days = System.getenv("MELISIM_OUTBOX_RETENTION_DAYS")?.toLongOrNull() ?: 7L
        val cutoff = Instant.now().minus(days, ChronoUnit.DAYS)
        val deleted = repository.deleteSentBefore(cutoff)
        log.info("outbox cleanup: deleted {} SENT rows older than {} ({} days)", deleted, cutoff, days)
    }
}
