package com.melisim.orders.outbox

import com.fasterxml.jackson.databind.ObjectMapper
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component
import org.springframework.transaction.annotation.Propagation
import org.springframework.transaction.annotation.Transactional

/**
 * Stores events in the outbox table in the SAME DB transaction as the business write.
 * The separate {@link OutboxPublisherWorker} ships them to Kafka later.
 */
@Component
class OutboxPublisher(
    private val repository: OutboxRepository,
    private val mapper: ObjectMapper,
) {
    private val log = LoggerFactory.getLogger(javaClass)

    @Transactional(propagation = Propagation.MANDATORY)
    fun stage(aggregateType: String, aggregateId: Long, eventType: String, topic: String, payload: Any) {
        val row = OutboxEvent(
            aggregateType = aggregateType,
            aggregateId = aggregateId,
            eventType = eventType,
            topic = topic,
            payload = mapper.writeValueAsString(payload),
        )
        repository.save(row)
        log.debug("staged outbox event id={} type={} topic={}", row.id, eventType, topic)
    }
}
