package com.melisim.orders.repository

import com.melisim.orders.model.Order
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.stereotype.Repository

@Repository
interface OrderRepository : JpaRepository<Order, Long> {
    fun findByBuyerId(buyerId: Long): List<Order>
}
