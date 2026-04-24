package com.melisim.orders.service

import com.melisim.orders.client.InsufficientStockException
import com.melisim.orders.client.ProductsClient
import com.melisim.orders.dto.CreateOrderRequest
import com.melisim.orders.dto.OrderResponse
import com.melisim.orders.event.OrderEventPublisher
import com.melisim.orders.model.Order
import com.melisim.orders.model.OrderStatus
import com.melisim.orders.repository.OrderRepository
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.math.BigDecimal

class OrderNotFoundException(message: String) : RuntimeException(message)
class IllegalStatusTransitionException(message: String) : RuntimeException(message)

@Service
class OrderService(
    private val repository: OrderRepository,
    private val productsClient: ProductsClient,
    private val publisher: OrderEventPublisher,
) {

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

        runCatching { productsClient.decrementStock(req.productId, req.quantity) }
        publisher.orderCreated(resp)
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
