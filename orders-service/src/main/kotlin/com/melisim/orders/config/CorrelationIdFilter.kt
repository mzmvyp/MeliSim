package com.melisim.orders.config

import jakarta.servlet.FilterChain
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.slf4j.MDC
import org.springframework.core.Ordered
import org.springframework.core.annotation.Order
import org.springframework.stereotype.Component
import org.springframework.web.filter.OncePerRequestFilter
import java.util.UUID

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
class CorrelationIdFilter : OncePerRequestFilter() {
    override fun doFilterInternal(req: HttpServletRequest, res: HttpServletResponse, chain: FilterChain) {
        val rid = req.getHeader(HEADER).takeUnless { it.isNullOrBlank() }
            ?: UUID.randomUUID().toString().replace("-", "")
        MDC.put(MDC_KEY, rid)
        res.setHeader(HEADER, rid)
        try {
            chain.doFilter(req, res)
        } finally {
            MDC.remove(MDC_KEY)
        }
    }

    companion object {
        const val HEADER = "X-Request-ID"
        const val MDC_KEY = "request_id"
    }
}
