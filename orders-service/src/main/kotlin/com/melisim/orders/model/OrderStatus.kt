package com.melisim.orders.model

enum class OrderStatus {
    CREATED,
    PAYMENT_PENDING,
    PAID,
    SHIPPED,
    DELIVERED,
    CANCELLED;

    fun canTransitionTo(next: OrderStatus): Boolean = when (this) {
        CREATED -> next in setOf(PAYMENT_PENDING, PAID, CANCELLED)
        PAYMENT_PENDING -> next in setOf(PAID, CANCELLED)
        PAID -> next in setOf(SHIPPED, CANCELLED)
        SHIPPED -> next == DELIVERED
        DELIVERED, CANCELLED -> false
    }
}
