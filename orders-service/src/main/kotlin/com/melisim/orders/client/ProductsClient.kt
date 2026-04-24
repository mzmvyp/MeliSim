package com.melisim.orders.client

import org.springframework.beans.factory.annotation.Value
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Component
import org.springframework.web.client.HttpClientErrorException
import org.springframework.web.client.RestClient
import java.math.BigDecimal

data class ProductSnapshot(
    val id: Long,
    val title: String,
    val price: BigDecimal,
    val stock: Int,
)

class ProductNotFoundException(message: String) : RuntimeException(message)
class InsufficientStockException(message: String) : RuntimeException(message)

@Component
class ProductsClient(
    @Value("\${melisim.products-service-url}") baseUrl: String,
) {
    private val client: RestClient = RestClient.builder().baseUrl(baseUrl).build()

    fun getProduct(id: Long): ProductSnapshot {
        return try {
            client.get().uri("/products/{id}", id)
                .retrieve()
                .body(ProductSnapshot::class.java)
                ?: throw ProductNotFoundException("Product $id not found (empty body)")
        } catch (e: HttpClientErrorException) {
            if (e.statusCode == HttpStatus.NOT_FOUND) {
                throw ProductNotFoundException("Product $id not found")
            }
            throw e
        }
    }

    fun decrementStock(productId: Long, qty: Int) {
        client.patch().uri("/products/{id}/stock", productId)
            .body(mapOf("delta" to -qty))
            .retrieve()
            .toBodilessEntity()
    }
}
