package com.melisim.orders.outbox

import org.springframework.data.domain.Pageable
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Lock
import org.springframework.data.jpa.repository.Query
import org.springframework.stereotype.Repository

import jakarta.persistence.LockModeType

@Repository
interface OutboxRepository : JpaRepository<OutboxEvent, Long> {

    /**
     * Fetch a batch of pending events with a pessimistic lock so multiple
     * worker instances don't ship the same row twice.
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
        SELECT e FROM OutboxEvent e
        WHERE e.status = com.melisim.orders.outbox.OutboxStatus.PENDING
        ORDER BY e.createdAt ASC
    """)
    fun lockPending(pageable: Pageable): List<OutboxEvent>
}
