package com.melisim.orders.dto

import com.melisim.orders.model.Order
import com.melisim.orders.model.OrderStatus
import jakarta.validation.constraints.Min
import jakarta.validation.constraints.NotNull
import java.math.BigDecimal
import java.time.Instant

data class CreateOrderRequest(
    @field:NotNull val buyerId: Long?,
    @field:NotNull val productId: Long?,
    @field:NotNull @field:Min(1) val quantity: Int?,
)

data class OrderResponse(
    val id: Long,
    val buyerId: Long,
    val productId: Long,
    val quantity: Int,
    val unitPrice: BigDecimal,
    val totalAmount: BigDecimal,
    val status: OrderStatus,
    val createdAt: Instant,
    val updatedAt: Instant,
) {
    companion object {
        fun from(o: Order) = OrderResponse(
            id = o.id!!,
            buyerId = o.buyerId,
            productId = o.productId,
            quantity = o.quantity,
            unitPrice = o.unitPrice,
            totalAmount = o.totalAmount,
            status = o.status,
            createdAt = o.createdAt,
            updatedAt = o.updatedAt,
        )
    }
}

data class UpdateStatusRequest(
    @field:NotNull val status: OrderStatus?,
)
