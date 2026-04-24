package com.melisim.orders.client

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker
import io.github.resilience4j.retry.annotation.Retry
import org.springframework.beans.factory.annotation.Value
import org.springframework.http.HttpStatus
import org.springframework.http.client.SimpleClientHttpRequestFactory
import org.springframework.stereotype.Component
import org.springframework.web.client.HttpClientErrorException
import org.springframework.web.client.RestClient
import java.math.BigDecimal
import java.time.Duration

data class ProductSnapshot(
    val id: Long,
    val title: String,
    val price: BigDecimal,
    val stock: Int,
)

class ProductNotFoundException(message: String) : RuntimeException(message)
class InsufficientStockException(message: String) : RuntimeException(message)
class ProductsUnavailableException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)

/**
 * Talks to products-service. Wrapped in a circuit breaker + retry (Resilience4j).
 * - CB: opens after 50% failure rate in a 20-call window, half-opens after 10s.
 * - Retry: up to 3 attempts with exponential backoff starting at 200ms.
 * - Explicit connect (2s) and read (3s) timeouts.
 */
@Component
class ProductsClient(
    @Value("\${melisim.products-service-url}") baseUrl: String,
) {
    private val client: RestClient = RestClient.builder()
        .baseUrl(baseUrl)
        .requestFactory(
            SimpleClientHttpRequestFactory().apply {
                setConnectTimeout(Duration.ofSeconds(2))
                setReadTimeout(Duration.ofSeconds(3))
            }
        )
        .build()

    @CircuitBreaker(name = "products", fallbackMethod = "getProductFallback")
    @Retry(name = "products")
    fun getProduct(id: Long): ProductSnapshot {
        return try {
            client.get().uri("/products/{id}", id)
                .retrieve()
                .body(ProductSnapshot::class.java)
                ?: throw ProductNotFoundException("Product $id not found (empty body)")
        } catch (e: HttpClientErrorException) {
            if (e.statusCode == HttpStatus.NOT_FOUND) {
                // 4xx — don't retry, don't count as CB failure
                throw ProductNotFoundException("Product $id not found")
            }
            throw e
        }
    }

    @Suppress("unused")
    private fun getProductFallback(id: Long, t: Throwable): ProductSnapshot {
        // Re-throwing a domain exception is acceptable — CB will still count it as a failure
        // but the caller gets a useful error instead of a raw timeout/IO exception.
        throw ProductsUnavailableException("products-service unavailable for id=$id: ${t.message}", t)
    }

    @CircuitBreaker(name = "products")
    @Retry(name = "products")
    fun decrementStock(productId: Long, qty: Int) {
        client.patch().uri("/products/{id}/stock", productId)
            .body(mapOf("delta" to -qty))
            .retrieve()
            .toBodilessEntity()
    }
}
