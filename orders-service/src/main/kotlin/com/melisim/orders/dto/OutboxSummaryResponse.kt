package com.melisim.orders.dto

import java.time.Instant

data class OutboxSummaryResponse(
    val pending: Long,
    val sentTotal: Long,
    val sentLast24Hours: Long,
    val failed: Long,
    val checkedAt: Instant,
)
