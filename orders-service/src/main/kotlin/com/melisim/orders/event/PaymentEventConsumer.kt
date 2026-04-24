package com.melisim.orders.event

import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.ObjectMapper
import com.melisim.orders.model.OrderStatus
import com.melisim.orders.service.OrderService
import org.slf4j.LoggerFactory
import org.springframework.kafka.annotation.KafkaListener
import org.springframework.stereotype.Component

@Component
class PaymentEventConsumer(
    private val orderService: OrderService,
    private val mapper: ObjectMapper,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    @KafkaListener(topics = ["payment-confirmed"], groupId = "orders-service")
    fun onPaymentConfirmed(message: String) {
        try {
            val node: JsonNode = mapper.readTree(message)
            val orderId = node.path("order_id").asLong(0L)
            if (orderId <= 0) {
                log.warn("payment-confirmed with no order_id: {}", message)
                return
            }
            orderService.updateStatus(orderId, OrderStatus.PAID)
            log.info("order {} moved to PAID after payment-confirmed", orderId)
        } catch (e: Exception) {
            log.error("failed to process payment-confirmed: {}", e.message, e)
        }
    }

    @KafkaListener(topics = ["payment-failed"], groupId = "orders-service")
    fun onPaymentFailed(message: String) {
        try {
            val node: JsonNode = mapper.readTree(message)
            val orderId = node.path("order_id").asLong(0L)
            if (orderId > 0) {
                orderService.updateStatus(orderId, OrderStatus.CANCELLED)
                log.info("order {} CANCELLED after payment-failed", orderId)
            }
        } catch (e: Exception) {
            log.error("failed to process payment-failed: {}", e.message, e)
        }
    }
}
