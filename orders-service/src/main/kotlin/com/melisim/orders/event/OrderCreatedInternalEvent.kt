package com.melisim.orders.event

/**
 * In-process Spring application event. Distinct from the Kafka `order-created`
 * event published via the outbox: this one is dispatched synchronously inside
 * the JVM after the order tx commits, used to trigger side-effects (e.g.
 * stock decrement on products-service) without holding the DB transaction
 * during the remote call.
 */
data class OrderCreatedInternalEvent(
    val orderId: Long,
    val productId: Long,
    val quantity: Int,
)
