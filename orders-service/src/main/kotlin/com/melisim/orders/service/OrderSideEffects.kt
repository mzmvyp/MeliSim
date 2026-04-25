package com.melisim.orders.service

import com.melisim.orders.client.ProductsClient
import com.melisim.orders.event.OrderCreatedInternalEvent
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component
import org.springframework.transaction.event.TransactionPhase
import org.springframework.transaction.event.TransactionalEventListener

/**
 * Listens for committed orders and fires the remote side-effects that don't
 * belong inside the DB transaction.
 *
 * Why AFTER_COMMIT and not the request thread?
 *   - The order is durable the moment the DB tx commits. We MUST NOT hold the
 *     transaction open while waiting for HTTP.
 *   - If the HTTP call fails, the order remains committed and the
 *     stock-update event the outbox publishes is still consumed by anyone
 *     who cares — products-service has its own ApplyStockDelta endpoint and
 *     a reconciliation job (stock-monitor) catches drift.
 *   - Resilience4j (CircuitBreaker + Retry on ProductsClient) absorbs
 *     transient failures here, isolated from the order write path.
 */
@Component
class OrderSideEffects(private val productsClient: ProductsClient) {

    private val log = LoggerFactory.getLogger(javaClass)

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    fun onOrderCreated(event: OrderCreatedInternalEvent) {
        runCatching { productsClient.decrementStock(event.productId, event.quantity) }
            .onFailure {
                log.warn(
                    "decrementStock failed orderId={} productId={} qty={} err={}",
                    event.orderId, event.productId, event.quantity, it.message,
                )
            }
    }
}
