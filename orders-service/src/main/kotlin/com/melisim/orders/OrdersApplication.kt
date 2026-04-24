package com.melisim.orders

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.kafka.annotation.EnableKafka

@SpringBootApplication
@EnableKafka
class OrdersApplication

fun main(args: Array<String>) {
    runApplication<OrdersApplication>(*args)
}
