package com.melisim.orders.outbox

import jakarta.persistence.*
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.Instant

enum class OutboxStatus { PENDING, SENT, FAILED }

@Entity
@Table(name = "outbox_events")
class OutboxEvent(
    @Column(name = "aggregate_type", nullable = false, length = 60)
    var aggregateType: String = "",

    @Column(name = "aggregate_id", nullable = false)
    var aggregateId: Long = 0,

    @Column(name = "event_type", nullable = false, length = 60)
    var eventType: String = "",

    @Column(nullable = false, length = 120)
    var topic: String = "",

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "JSON")
    var payload: String = "{}",

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    var status: OutboxStatus = OutboxStatus.PENDING,
) {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null

    @Column(nullable = false)
    var attempts: Int = 0

    @Column(name = "last_error", columnDefinition = "TEXT")
    var lastError: String? = null

    @Column(name = "created_at", updatable = false)
    var createdAt: Instant = Instant.now()

    @Column(name = "sent_at")
    var sentAt: Instant? = null
}
