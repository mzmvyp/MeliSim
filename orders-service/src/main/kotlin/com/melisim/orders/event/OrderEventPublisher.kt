package com.melisim.orders.event

import com.fasterxml.jackson.databind.ObjectMapper
import com.melisim.orders.dto.OrderResponse
import org.slf4j.LoggerFactory
import org.springframework.kafka.core.KafkaTemplate
import org.springframework.stereotype.Component

@Component
class OrderEventPublisher(
    private val kafkaTemplate: KafkaTemplate<String, String>,
    private val mapper: ObjectMapper,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    fun orderCreated(order: OrderResponse) {
        try {
            val payload = mapper.writeValueAsString(order)
            kafkaTemplate.send("order-created", order.id.toString(), payload)
            log.info("published order-created for id={}", order.id)
        } catch (e: Exception) {
            log.warn("failed to publish order-created: {}", e.message)
        }
    }
}
