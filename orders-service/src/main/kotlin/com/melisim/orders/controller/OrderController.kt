package com.melisim.orders.controller

import com.melisim.orders.client.InsufficientStockException
import com.melisim.orders.client.ProductNotFoundException
import com.melisim.orders.dto.CreateOrderRequest
import com.melisim.orders.dto.OrderResponse
import com.melisim.orders.dto.UpdateStatusRequest
import com.melisim.orders.service.IllegalStatusTransitionException
import com.melisim.orders.service.OrderNotFoundException
import com.melisim.orders.service.OrderService
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*
import java.time.Instant

@RestController
@RequestMapping("/orders")
class OrderController(private val service: OrderService) {

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    fun create(@Valid @RequestBody req: CreateOrderRequest): OrderResponse = service.create(req)

    @GetMapping("/{id}")
    fun get(@PathVariable id: Long): OrderResponse = service.getById(id)

    @GetMapping("/user/{userId}")
    fun byUser(@PathVariable userId: Long): List<OrderResponse> = service.findByBuyer(userId)

    @PatchMapping("/{id}/status")
    fun updateStatus(
        @PathVariable id: Long,
        @Valid @RequestBody req: UpdateStatusRequest,
    ): OrderResponse = service.updateStatus(id, req.status!!)

    @GetMapping("/health")
    fun health(): Map<String, String> =
        mapOf("status" to "ok", "service" to "orders-service")

    @ExceptionHandler(OrderNotFoundException::class, ProductNotFoundException::class)
    fun notFound(e: RuntimeException) = problem(HttpStatus.NOT_FOUND, e.message ?: "not found")

    @ExceptionHandler(InsufficientStockException::class, IllegalStatusTransitionException::class, IllegalArgumentException::class)
    fun badRequest(e: RuntimeException) = problem(HttpStatus.BAD_REQUEST, e.message ?: "bad request")

    private fun problem(status: HttpStatus, message: String) =
        ResponseEntity.status(status).body(
            mapOf(
                "timestamp" to Instant.now().toString(),
                "status" to status.value(),
                "error" to status.reasonPhrase,
                "message" to message,
            )
        )
}
