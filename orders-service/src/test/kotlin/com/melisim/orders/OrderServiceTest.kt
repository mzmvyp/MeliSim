package com.melisim.orders

import com.melisim.orders.client.InsufficientStockException
import com.melisim.orders.client.ProductSnapshot
import com.melisim.orders.client.ProductsClient
import com.melisim.orders.dto.CreateOrderRequest
import com.melisim.orders.event.OrderEventPublisher
import com.melisim.orders.model.Order
import com.melisim.orders.model.OrderStatus
import com.melisim.orders.repository.OrderRepository
import com.melisim.orders.service.IllegalStatusTransitionException
import com.melisim.orders.service.OrderNotFoundException
import com.melisim.orders.service.OrderService
import io.mockk.Runs
import io.mockk.every
import io.mockk.just
import io.mockk.mockk
import io.mockk.verify
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.math.BigDecimal
import java.util.Optional

class OrderServiceTest {

    private val repo = mockk<OrderRepository>()
    private val products = mockk<ProductsClient>()
    private val publisher = mockk<OrderEventPublisher>(relaxed = true)
    private val service = OrderService(repo, products, publisher)

    @Test
    fun `create success calculates total and publishes event`() {
        every { products.getProduct(7L) } returns ProductSnapshot(7L, "Book", BigDecimal("50.00"), 10)
        every { products.decrementStock(7L, 2) } just Runs
        every { repo.save(any<Order>()) } answers {
            val o = firstArg<Order>()
            o.id = 1L
            o
        }

        val resp = service.create(CreateOrderRequest(buyerId = 1, productId = 7, quantity = 2))

        assertThat(resp.status).isEqualTo(OrderStatus.CREATED)
        assertThat(resp.totalAmount).isEqualByComparingTo(BigDecimal("100.00"))
        verify { publisher.orderCreated(any()) }
    }

    @Test
    fun `create rejects when stock insufficient`() {
        every { products.getProduct(7L) } returns ProductSnapshot(7L, "Book", BigDecimal("50.00"), 1)

        assertThatThrownBy {
            service.create(CreateOrderRequest(buyerId = 1, productId = 7, quantity = 5))
        }.isInstanceOf(InsufficientStockException::class.java)

        verify(exactly = 0) { repo.save(any<Order>()) }
    }

    @Test
    fun `updateStatus rejects invalid transition`() {
        val o = Order(buyerId = 1, productId = 7, quantity = 1,
            unitPrice = BigDecimal.TEN, totalAmount = BigDecimal.TEN,
            status = OrderStatus.DELIVERED).apply { id = 1L }
        every { repo.findById(1L) } returns Optional.of(o)

        assertThatThrownBy {
            service.updateStatus(1L, OrderStatus.CREATED)
        }.isInstanceOf(IllegalStatusTransitionException::class.java)
    }

    @Test
    fun `getById missing throws not-found`() {
        every { repo.findById(99L) } returns Optional.empty()
        assertThatThrownBy { service.getById(99L) }
            .isInstanceOf(OrderNotFoundException::class.java)
    }

    @Test
    fun `updateStatus paid transitions successfully`() {
        val o = Order(buyerId = 1, productId = 7, quantity = 1,
            unitPrice = BigDecimal.TEN, totalAmount = BigDecimal.TEN,
            status = OrderStatus.CREATED).apply { id = 1L }
        every { repo.findById(1L) } returns Optional.of(o)
        every { repo.save(o) } returns o

        val resp = service.updateStatus(1L, OrderStatus.PAID)
        assertThat(resp.status).isEqualTo(OrderStatus.PAID)
    }
}
