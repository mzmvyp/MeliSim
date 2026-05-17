package com.melisim.orders.controller

import com.melisim.orders.dto.OutboxSummaryResponse
import com.melisim.orders.outbox.OutboxRepository
import com.melisim.orders.outbox.OutboxStatus
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * Internal admin metrics for the transactional outbox (orders-service).
 * Protected at the API gateway — only ADMIN JWT may call /api/v1/admin/outbox/… from browsers.
 */
@RestController
@RequestMapping("/admin/outbox")
class OutboxAdminController(private val repository: OutboxRepository) {

    @GetMapping("/summary")
    fun summary(): OutboxSummaryResponse {
        val now = Instant.now()
        val dayAgo = now.minus(24, ChronoUnit.HOURS)
        return OutboxSummaryResponse(
            pending = repository.countByStatus(OutboxStatus.PENDING),
            sentTotal = repository.countByStatus(OutboxStatus.SENT),
            sentLast24Hours = repository.countByStatusAndSentAtAfter(OutboxStatus.SENT, dayAgo),
            failed = repository.countByStatus(OutboxStatus.FAILED),
            checkedAt = now,
        )
    }
}
