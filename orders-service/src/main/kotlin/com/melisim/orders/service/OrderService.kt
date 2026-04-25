package com.melisim.orders.service

import com.melisim.orders.client.InsufficientStockException
import com.melisim.orders.client.ProductsClient
import com.melisim.orders.dto.CreateOrderRequest
import com.melisim.orders.dto.OrderResponse
import com.melisim.orders.event.OrderCreatedInternalEvent
import com.melisim.orders.model.Order
import com.melisim.orders.model.OrderStatus
import com.melisim.orders.outbox.OutboxPublisher
import com.melisim.orders.repository.OrderRepository
import org.slf4j.LoggerFactory
import org.springframework.context.ApplicationEventPublisher
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.math.BigDecimal

class OrderNotFoundException(message: String) : RuntimeException(message)
class IllegalStatusTransitionException(message: String) : RuntimeException(message)

@Service
class OrderService(
    private val repository: OrderRepository,
    private val productsClient: ProductsClient,
    private val outbox: OutboxPublisher,
    private val events: ApplicationEventPublisher,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    /**
     * Create + outbox-stage in one DB transaction. The remote stock decrement is
     * fired AFTER COMMIT via Spring's ApplicationEventPublisher, handled in
     * [OrderSideEffects]. This way:
     *   - The DB connection is released BEFORE the HTTP call, so a slow
     *     products-service doesn't starve the connection pool.
     *   - If decrementStock fails, the order is already committed — eventually
     *     consistent, recoverable through the inventory reconciliation job.
     */
    @Transactional
    fun create(req: CreateOrderRequest): OrderResponse {
        require(req.buyerId != null && req.buyerId > 0) { "buyerId is required" }
        require(req.productId != null && req.productId > 0) { "productId is required" }
        require(req.quantity != null && req.quantity > 0) { "quantity must be > 0" }

        val product = productsClient.getProduct(req.productId)
        if (product.stock < req.quantity) {
            throw InsufficientStockException(
                "Insufficient stock: requested=${req.quantity}, available=${product.stock}"
            )
        }

        val order = Order(
            buyerId = req.buyerId,
            productId = req.productId,
            quantity = req.quantity,
            unitPrice = product.price,
            totalAmount = product.price.multiply(BigDecimal(req.quantity)),
            status = OrderStatus.CREATED,
        )
        val saved = repository.save(order)
        val resp = OrderResponse.from(saved)

        outbox.stage(
            aggregateType = "order",
            aggregateId = saved.id!!,
            eventType = "order-created",
            topic = "order-created",
            payload = resp,
        )

        // Hand off the remote side-effect to an after-commit listener.
        events.publishEvent(OrderCreatedInternalEvent(saved.id!!, req.productId, req.quantity))
        return resp
    }

    @Transactional(readOnly = true)
    fun getById(id: Long): OrderResponse {
        val o = repository.findById(id).orElseThrow { OrderNotFoundException("Order $id not found") }
        return OrderResponse.from(o)
    }

    @Transactional(readOnly = true)
    fun findByBuyer(buyerId: Long): List<OrderResponse> =
        repository.findByBuyerId(buyerId).map(OrderResponse::from)

    @Transactional
    fun updateStatus(id: Long, next: OrderStatus): OrderResponse {
        val o = repository.findById(id).orElseThrow { OrderNotFoundException("Order $id not found") }
        if (!o.status.canTransitionTo(next)) {
            throw IllegalStatusTransitionException(
                "Cannot transition order $id from ${o.status} to $next"
            )
        }
        o.status = next
        return OrderResponse.from(repository.save(o))
    }
}
