# MeliSim — Guia de Estudo & Entrevista Técnica

Documento completo do sistema, escrito para você **estudar e apresentar** o projeto em uma entrevista técnica. Cobre arquitetura, decisões, padrões implementados, e walkthrough de cada arquivo.

---

## Sumário

- **[Parte I — Visão Geral](#parte-i--visão-geral)**
  - 1. O que é o MeliSim
  - 2. Stack em 30 segundos
  - 3. Por que polyglot
- **[Parte II — Decisões de Arquitetura](#parte-ii--decisões-de-arquitetura)**
  - 4. Microserviços vs monolito
  - 5. Comunicação síncrona vs assíncrona
  - 6. Bancos de dados (MySQL vs Postgres vs Redis vs ES)
  - 7. Por que Kafka
- **[Parte III — Padrões Implementados (com código)](#parte-iii--padrões-implementados)**
  - 8. Transactional Outbox
  - 9. Circuit Breaker + Retry (Resilience4j)
  - 10. Idempotency-Key
  - 11. After-commit event listener
  - 12. Dead Letter Queue
  - 13. Distributed sliding-window rate limiter
  - 14. Correlation ID + distributed tracing
  - 15. Health checks live/ready
  - 16. Graceful shutdown
- **[Parte IV — Tour pelos Serviços](#parte-iv--tour-pelos-serviços)**
- **[Parte V — Catálogo de Arquivos](#parte-v--catálogo-de-arquivos)**
- **[Parte VI — Como Apresentar na Entrevista](#parte-vi--como-apresentar-na-entrevista)**
- **[Parte VII — Glossário](#parte-vii--glossário)**

---

# Parte I — Visão Geral

## 1. O que é o MeliSim

Marketplace simulado nos moldes do Mercado Livre, com 8 microserviços em 4 linguagens (Python, Java, Kotlin, Go), 4 bancos/brokers (MySQL, PostgreSQL, Redis, Kafka), full-text search com Elasticsearch e stack de observabilidade completa (Prometheus + Grafana + Jaeger).

**O que demonstra:**
- Arquitetura distribuída orientada a eventos
- Padrões de resiliência (CB, retry, timeout, bulkhead)
- Padrões de consistência distribuída (Outbox, Idempotency, after-commit)
- Observabilidade dos 3 pilares (metrics, traces, logs com correlation)
- DevEx (Makefile, Docker, CI multi-linguagem com gates de segurança)

**O que NÃO é:**
- Não é production-grade (defaults de lab — Grafana admin/admin, JWT secret no compose)
- Não tem service mesh / mTLS interno
- Não tem schema registry / Avro / Protobuf nos eventos Kafka

## 2. Stack em 30 segundos

```
api-gateway (Python)        ← entrada, JWT, rate limit Redis, correlation
users-service (Java)        ← BCrypt + JWT issuer
products-service (Go)       ← catálogo, cache Redis, publica stock-updates
orders-service (Kotlin)     ← Outbox + Resilience4j + after-commit listener
payments-service (Python)   ← idempotency-key, simulador de gateway
notifications-service       ← consumer multi-tópico com DLQ
search-service              ← Elasticsearch, indexa via eventos
stock-monitor (Go)          ← job periódico, publica stock-alert
+ Kafka, MySQL, Postgres, Redis, ES, Prometheus, Grafana, Jaeger
```

## 3. Por que polyglot

Cada linguagem foi escolhida pelo encaixe com a natureza do serviço — não para "mostrar que sabe":

| Linguagem | Serviço | Por quê |
|---|---|---|
| **Python/FastAPI** | gateway, payments, notifications, search | I/O-heavy, async-first, validação Pydantic, ecossistema rico em integrações |
| **Java/Spring Boot** | users | Stack maduro de identidade/segurança (BCrypt + Spring Security + JJWT é "boring in a good way") |
| **Kotlin/Spring Boot** | orders | Domain-rich (transições de status, totais, outbox) lê melhor em Kotlin que Java mantendo Spring |
| **Go** | products, stock-monitor | Hot-path do catálogo se beneficia da concorrência leve; binário-sem-runtime do Go é ideal para um worker scheduled como o stock-monitor |

---

# Parte II — Decisões de Arquitetura

## 4. Microserviços vs monolito

**Trade-off real:** monolito é mais simples até virar muleta. Aqui escolhi microserviços porque o domínio tem fronteiras naturais (catálogo, pedido, pagamento) e cada um teria perfil de carga e SLA diferentes:
- `products-service` é leitura intensa, cacheável → escala horizontal stateless
- `payments-service` tem espera externa (PSP) e idempotência crítica
- `search-service` é uma view derivada — perfeito para CQRS

**Custo pago:** consistência eventual entre catálogo/pedido/pagamento, complexidade operacional (8 deploys, 8 monitores). Endereçado com Outbox + observability completa.

**Resposta para entrevista:** "Microserviços não foram escolhidos por moda. Os bounded contexts são distintos, com SLAs diferentes e padrões de escalabilidade diferentes — separar permite escalar `products` para 20 réplicas sem dobrar o `payments`."

## 5. Comunicação síncrona vs assíncrona

| Caso | Modo | Por quê |
|---|---|---|
| `gateway → users` (login) | Sync HTTP | O usuário precisa do JWT na mesma resposta |
| `orders → products` (verificar estoque) | Sync HTTP | Validação síncrona do estoque é UX |
| `orders` publica `order-created` | **Async (Kafka via Outbox)** | Notificação não bloqueia confirmação do pedido |
| `payments` publica `payment-confirmed` | Async | Atualiza status de pedido + envia recibo em paralelo |

**Princípio:** "**ask synchronously, tell asynchronously**". Quando o caller precisa da resposta para continuar — sync. Quando é uma notificação ("aconteceu X") — async via Kafka.

## 6. Bancos de dados

| Tecnologia | Onde | Por quê |
|---|---|---|
| **MySQL** | users, orders | Carga transacional clássica, identidade. JPA/Hibernate. |
| **PostgreSQL** | products, payments, notifications | Tipos ricos (NUMERIC, JSON), full-text fallback, melhor performance em workloads analíticos leves |
| **Redis** | cache (products), rate limiter (gateway) | Sub-millisecond para hot reads, atomic ops para sliding window |
| **Elasticsearch** | search-service | Search relevance + autocomplete (`completion` field) — Postgres FTS funciona, mas relevância é fraca |

**Truque comum em entrevista:** "Por que não tudo Postgres?" — Resposta: poderia. Postgres+pg_trgm+tsvector cobre 80% do search. Elasticsearch entrou porque queria demonstrar o padrão **CQRS leve** (write model em Postgres, read model em ES indexado via eventos Kafka).

## 7. Por que Kafka (e não RabbitMQ/SQS)

- **Replay**: poder reler eventos do início é o que permite reconstruir o índice de search após adicionar um campo novo. RabbitMQ não tem isso nativo.
- **Particionamento por chave**: garante ordem por `order_id` sem pegar lock global.
- **Throughput**: dimensionado para milhões de mensagens/s — futuro-prova.
- **Padrão de mercado**: o que entrevistador espera ouvir.

Custo: complexidade operacional alta (Zookeeper/KRaft, partições, consumer lag). Mitigado aqui usando Confluent Platform images.

---

# Parte III — Padrões Implementados

## 8. Transactional Outbox

**Problema:** dual-write. Se você grava no DB e publica no Kafka em sequência, qualquer falha entre os dois passos deixa o sistema inconsistente — pedido sem evento, ou evento sem pedido.

**Solução implementada (orders-service):**
1. Na mesma `@Transactional`, salva o pedido **e** insere o evento na tabela `outbox_events` (status `PENDING`).
2. Worker `@Scheduled` (`OutboxPublisherWorker`) faz polling com **PESSIMISTIC_WRITE lock** — múltiplas instâncias não pegam a mesma linha.
3. Faz `kafka.send()` em **pipeline** (todas as futures em paralelo, depois `.get()` em cada uma) para aproveitar batching do producer.
4. Marca como `SENT` ou incrementa `attempts`. Após 10 falhas → `FAILED` (rico no dashboard Grafana).
5. Worker noturno (`OutboxCleanupWorker`) deleta `SENT` > 7 dias.

**Arquivos:**
- `orders-service/src/main/resources/db/migration/V2__outbox.sql`
- `orders-service/src/main/kotlin/com/melisim/orders/outbox/OutboxEvent.kt`
- `OutboxRepository.kt` (com `lockPending` e `deleteSentBefore`)
- `OutboxPublisher.kt` — chamado de dentro de `@Transactional` no service
- `OutboxPublisherWorker.kt` — pipeline + métricas
- `OutboxCleanupWorker.kt` — GC noturno

**Pergunta provável:** "E se o worker reiniciar no meio?"
**Resposta:** "O lock pessimista é mantido apenas durante a transação. Se cair, as linhas voltam para `PENDING` e o próximo poll pega. Pior caso: at-least-once delivery (pode duplicar). Por isso eventos têm `event_id` e consumidores devem ser idempotentes."

## 9. Circuit Breaker + Retry (Resilience4j)

**Implementado em:** `orders-service/src/main/kotlin/com/melisim/orders/client/ProductsClient.kt`

```kotlin
@CircuitBreaker(name = "products", fallbackMethod = "getProductFallback")
@Retry(name = "products")
fun getProduct(id: Long): ProductSnapshot { ... }
```

**Tuning** (`application.yml`):
- **CB**: abre com 50% falhas em janela de 20 chamadas, half-open após 10s, permite 3 chamadas test em half-open
- **Retry**: 3 tentativas com backoff exponencial (200ms, 400ms, 800ms), só retenta em `IOException`/`HttpServerErrorException`
- **TimeLimiter**: 3s
- **Bulkhead**: max 25 chamadas concorrentes — uma upstream lenta não consome todo o Tomcat

**Por que essa ordem (Bulkhead → CB → Retry)?**
1. Bulkhead barra excesso de concorrência
2. CB short-circuits se serviço já está falhando
3. Retry tenta de novo apenas para falhas transientes (4xx NÃO retenta)

**Pergunta provável:** "Por que usar CB e Retry juntos?"
**Resposta:** "CB protege o caller de hammerar um serviço caído. Retry resolve o blip transiente de 1ms. Sem CB, retry torna a falha pior (retry storm). Sem retry, blips fazem requests do usuário falharem desnecessariamente."

## 10. Idempotency-Key (payments-service)

**Problema:** cliente faz POST /payments, o request demora, ele tenta de novo. Sem idempotency, cobra duas vezes.

**Solução:**
1. Header `Idempotency-Key: <uuid>` opcional.
2. Servidor calcula `fingerprint = sha256(canonical_json(body))`.
3. Lookup na tabela `idempotency_keys`:
   - **Não existe** → processa, salva `(key, fingerprint, response)`.
   - **Existe + mesmo fingerprint** → retorna response salvo + header `Idempotent-Replayed: true`.
   - **Existe + fingerprint diferente** → 422 Unprocessable Entity.

**Arquivos:**
- `payments-service/models/idempotency.py` — ORM
- `payments-service/services/idempotency_service.py` — lógica
- `payments-service/routes/payment_routes.py` — uso no endpoint
- `payments-service/tests/test_idempotency.py` — testes

**Pergunta provável:** "E se duas requests com a mesma chave chegarem ao mesmo tempo?"
**Resposta:** "Race condition real. A constraint UNIQUE no Postgres garante que só uma INSERT vence; a segunda pega `IntegrityError`, faz rollback, lê o registro vencedor e retorna o mesmo response. É AT-MOST-ONCE garantido pela DB."

## 11. After-commit event listener

**Problema:** `OrderService.create()` está `@Transactional`. Se eu chamar `productsClient.decrementStock()` lá dentro, **prendo a conexão de DB durante uma chamada HTTP** — sob carga, drena o pool.

**Solução:**
```kotlin
@Transactional
fun create(...): OrderResponse {
    repository.save(order)
    outbox.stage(...)
    events.publishEvent(OrderCreatedInternalEvent(...))  // só dispara se commit der OK
    return resp
}

@Component
class OrderSideEffects(...) {
    @TransactionalEventListener(phase = AFTER_COMMIT)
    fun onOrderCreated(event: OrderCreatedInternalEvent) {
        runCatching { productsClient.decrementStock(...) }
    }
}
```

**Arquivos:**
- `OrderService.kt` (publica via `ApplicationEventPublisher`)
- `OrderCreatedInternalEvent.kt` (data class)
- `OrderSideEffects.kt` (`@TransactionalEventListener(AFTER_COMMIT)`)

**Pergunta provável:** "E se a chamada após o commit falhar?"
**Resposta:** "Pedido fica committed, estoque fica errado temporariamente. Resilience4j absorve transient. Para casos persistentes, o `stock-monitor` é o reconciliador — ele detecta drift e alerta. A alternativa 'correta' seria publicar `stock-decrement-requested` no outbox e o `products-service` consumir, mas dobra a latência percebida — trade-off documentado."

## 12. Dead Letter Queue

**Implementado em:** `notifications-service/consumers/notification_consumer.py`

Cada handler de tópico:
1. Tenta processar.
2. Falha → retry com backoff (200ms → 400ms → 2s, max 3).
3. Ainda falha → publica em `<topic>.dlq` com envelope contendo: `original_topic`, `partition`, `offset`, `key`, `value`, `error_type`, `failed_at`.
4. **Commit do offset** acontece de qualquer forma — não bloqueia a partição com poison message.

**Tópicos DLQ:** `order-created.dlq`, `payment-confirmed.dlq`, `payment-failed.dlq`, `stock-alert.dlq` (criados em `infra/kafka/topics.sh` com 1 partição + 30 dias de retenção).

**Pergunta provável:** "Como fazer replay de DLQ?"
**Resposta:** "Operacional manual: ferramenta consome o DLQ, inspeciona, corrige (ou descarta), republica no tópico original. Em produção real, eu adicionaria um `dlq-replayer` service com endpoint admin."

## 13. Distributed sliding-window rate limiter

**Implementado em:** `api-gateway/middleware/rate_limiter_redis.py`

Algoritmo: **sorted set sliding window** com Lua script para atomicidade.

```lua
ZREMRANGEBYSCORE key 0 (now-window)   -- expira velhos
ZCARD key                              -- conta na janela
if count >= max then return DENY end
ZADD key now uniqueId                  -- adiciona atual
EXPIRE key (window+1)                  -- GC
return ALLOW
```

**Por que sorted set e não counter+EXPIRE?**
- Counter com TTL é **fixed window** — picos no minuto 59 e 01 viram 2x o limite.
- Sorted set dá janela deslizante de verdade.

**Por que Lua?**
- Garante que ZREMRANGEBYSCORE + ZCARD + ZADD aconteçam atomicamente. Sem Lua, dois requests paralelos podem ver o mesmo `count < max` e ambos passarem.

**Fail-open** se Redis cair: middleware loga e libera a request. Decisão consciente — limitador caído ≠ gateway caído. Em alta segurança, fail-closed.

## 14. Correlation ID + distributed tracing

Toda request entra no gateway → ganha `X-Request-ID` (UUID4 hex) ou usa o do header se já vier. ID:
- Vai para o **MDC** (Java/Kotlin) e **contextvar** (Python) → aparece em todo log JSON daquela request
- É repassado nas chamadas HTTP downstream (header `x-request-id` adicionado em `_proxy()` no router)
- É anexado como **span attribute** no OpenTelemetry → traces no Jaeger têm o mesmo ID dos logs

**Como demonstrar em entrevista:** "Pega um pedido com erro nos logs do notifications. Filtra por `request_id=abc123`. Encontra o trace no Jaeger com mesmo ID — vê os 3-4 saltos. Pinpoint do problema em 30 segundos."

**Arquivos:**
- `api-gateway/middleware/correlation.py` — gera/propaga
- `users-service/.../config/CorrelationIdFilter.java` — filter Spring + MDC
- `orders-service/.../config/CorrelationIdFilter.kt` — idem Kotlin
- `products-service/internal/observability/observability.go` — middleware Go

## 15. Health checks live/ready

| Endpoint | Significa | Quem usa |
|---|---|---|
| `/health/live` | "Processo está respondendo" | k8s liveness probe — reinicia se 503 |
| `/health/ready` | "Posso receber tráfego?" — checa DB, Kafka, upstream | k8s readiness probe — remove de Service se 503; load balancer pula |
| `/health` | Alias de `live` (compat) | Docker HEALTHCHECK |

**Diferença crítica:** liveness 503 → kill+restart. Readiness 503 → fora do pool, mas vivo (talvez DB temporariamente fora). Misturar os dois causa restart loop quando a dependência cai.

## 16. Graceful shutdown

Toda aplicação trata SIGTERM:
- **Spring**: `server.shutdown: graceful` + `spring.lifecycle.timeout-per-shutdown-phase: 15s` — drena requests in-flight, fecha pool de DB, para `@KafkaListener`.
- **Python (FastAPI)**: `lifespan` context manager — para Kafka consumer task, fecha engine SQLAlchemy, await tasks.
- **Go**: `signal.NotifyContext` + `srv.Shutdown(ctx)` com timeout de 10s.

**Por que importa:** durante deploy/scale-down, o pod ganha SIGTERM. Sem graceful, requests in-flight ganham 502. Com, drenam até 15s antes do SIGKILL.

---

# Parte IV — Tour pelos Serviços

## api-gateway (Python/FastAPI, porta 8000)

**Responsabilidade:** ponto único de entrada da rede pública. Não tem lógica de domínio.

**Camadas (de fora pra dentro do request):**
1. `CorrelationIdMiddleware` — gera/propaga `X-Request-ID`
2. `AuthMiddleware` — valida JWT (rotas listadas em `PUBLIC_PATHS` passam)
3. `RedisRateLimiterMiddleware` ou `RateLimiterMiddleware` — escolhido pelo `REDIS_URL`
4. `PrometheusMiddleware` — registra latência + count
5. CORS
6. OpenTelemetry FastAPI instrumentor + httpx instrumentor
7. Router → `_proxy()` → `httpx.AsyncClient` (singleton no app.state)

**O que destacar em entrevista:** "Não invento headers — `X-Request-ID` é repassado para todos os upstreams. Auth para na borda. Rate limit é distribuído via Redis Lua script."

## users-service (Java/Spring Boot, porta 8001)

**Responsabilidade:** identidade. Cadastro, autenticação, emissão de JWT.

**Stack:**
- Spring Security + BCryptPasswordEncoder
- JJWT 0.12 para emissão (HMAC SHA-256 com chave de 32+ bytes)
- Spring Data JPA + MySQL
- Flyway para schema (`V1__init_users.sql`)
- Validação Bean Validation no DTO (`@Email`, `@NotBlank`, `@Size(min=8)`)

**Endpoints:**
- `POST /users/register` (201)
- `POST /users/login` (200, retorna `TokenResponse`)
- `GET/PUT/DELETE /users/{id}` — gestão básica

**Tratamento de erros:** `GlobalExceptionHandler` mapeia exceções de domínio para HTTP status corretos (`UserNotFoundException` → 404, `EmailAlreadyExistsException` → 409, `MethodArgumentNotValidException` → 400 com detalhe).

## products-service (Go/chi, porta 8002)

**Responsabilidade:** catálogo. CRUD de produtos com cache.

**Camadas:**
- `cmd/main.go` — wiring (DB pool, Redis, Kafka publisher, router, graceful shutdown)
- `internal/handler/` — HTTP handlers
- `internal/service/` — lógica de negócio + cache-aside (interface `Cache` injetável → testável)
- `internal/repository/` — pgxpool com tuning explícito (max conns, idle timeout, health check)
- `internal/cache/` — Redis (`go-redis/v9`)
- `internal/events/` — `KafkaPublisher` (segmentio/kafka-go)
- `internal/observability/` — Prometheus middleware + correlation ID
- `internal/middleware/` — structured logger

**Hot path (`GET /products`):** consulta Redis → miss → consulta Postgres → grava cache TTL 5min. Invalidação targetada em writes (POST, PATCH stock).

**Padrão importante:** atualização de estoque com `UPDATE ... WHERE stock + delta >= 0 RETURNING ...` — evita estoque negativo via constraint da própria query, não em código.

## orders-service (Kotlin/Spring Boot, porta 8003)

**Responsabilidade:** ciclo de vida do pedido (CREATED → PAID → SHIPPED → DELIVERED ou CANCELLED).

**Padrões aplicados aqui:** Outbox + Resilience4j + after-commit listener + Flyway. **Esse é o serviço que mais "fala alto" em entrevista.**

**Estrutura:**
```
orders-service/src/main/kotlin/com/melisim/orders/
├── OrdersApplication.kt
├── controller/OrderController.kt
├── service/
│   ├── OrderService.kt           — write path (Outbox + ApplicationEventPublisher)
│   └── OrderSideEffects.kt       — @TransactionalEventListener(AFTER_COMMIT)
├── client/ProductsClient.kt       — @CircuitBreaker + @Retry
├── outbox/
│   ├── OutboxEvent.kt             — @Entity, JdbcTypeCode(JSON)
│   ├── OutboxRepository.kt        — lockPending + deleteSentBefore
│   ├── OutboxPublisher.kt         — chamado em @Transactional, MANDATORY
│   ├── OutboxPublisherWorker.kt   — @Scheduled, pipeline send
│   └── OutboxCleanupWorker.kt     — @Scheduled cron, GC noturno
├── event/
│   ├── OrderCreatedInternalEvent.kt
│   └── PaymentEventConsumer.kt    — @KafkaListener payment-confirmed/failed
├── model/Order.kt + OrderStatus.kt (state machine com canTransitionTo)
├── repository/OrderRepository.kt
├── dto/OrderDTO.kt
└── config/CorrelationIdFilter.kt
```

**State machine:** `OrderStatus.canTransitionTo(next)` — `DELIVERED` e `CANCELLED` são terminais, transições inválidas viram exception → 400.

## payments-service (Python/FastAPI, porta 8004)

**Responsabilidade:** processar pagamento (simulado com `asyncio.sleep(2)`).

**Diferencial:** **idempotência completa**. Header `Idempotency-Key` opcional, mas se vier, garante que retry não cobra duas vezes.

**Lógica de simulação** (`_simulate_processing`): amount >= 100k → FAILED (fraude); senão CONFIRMED. Determinístico para testes.

**Eventos publicados:** `payment-confirmed` ou `payment-failed` no Kafka, consumidos por `orders-service` e `notifications-service`.

**Pool tuning:** `pool_size=10, max_overflow=20, pool_pre_ping=True, pool_recycle=1800` — sobrevive a restart de DB e idle-kill de firewall.

## notifications-service (Python/FastAPI, porta 8005)

**Responsabilidade:** transformar eventos Kafka em "notificações" (simuladas — print no console + linha no Postgres).

**Padrões:** consumer multi-tópico com **retry interno + DLQ + commit manual**.

**Tópicos consumidos:** `order-created`, `payment-confirmed`, `payment-failed`, `stock-alert`. Cada um com handler dedicado em `services/notification_service.py`.

**Estratégia de falha:**
1. Handler falha → retry 3x com backoff (200ms, 400ms, 800ms)
2. Ainda falha → publica em `<topic>.dlq` com envelope rico
3. Commit do offset original — partição não trava

**Templates:** Jinja2 em `templates/*.html` (`order_confirmed`, `payment_confirmed`, `payment_failed`, `stock_alert`).

## search-service (Python/FastAPI, porta 8006)

**Responsabilidade:** read model do catálogo. Indexa via eventos, serve queries de busca + autocomplete.

**Padrão:** **CQRS leve**. Não tem write model — só consome `product-created` e `stock-updates` do Kafka e atualiza Elasticsearch.

**Endpoints:**
- `GET /search?q=...&category=...&min_price=...&max_price=...&size=...`
- `GET /search/suggestions?q=...&size=...` — usa `completion` field

**Query ES:** `bool` com `multi_match` (title^3, description, fuzziness AUTO) + filters de categoria/preço.

**Resiliente a ES caído:** `ensure_index()` é best-effort no startup, falha de search retorna lista vazia (loga warning). Em produção, melhor seria 503 explícito.

## stock-monitor (Go, porta 8099 só para metrics)

**Responsabilidade:** job periódico (a cada 60s) que detecta produtos com estoque baixo e publica `stock-alert`.

**Detalhe interessante:** formato do log de auditoria inspirado no problema HackerRank Q13 — `error_code,YYYY-MM-DD,server_id,endpoint`. É o padrão "aggregate errors by time bucket" que aparece em entrevistas.

**Sem servidor HTTP de aplicação** — só `/metrics` e `/health` na porta 8099. Container roda como worker.

---

# Parte V — Catálogo de Arquivos

> Por economia, agrupo onde fizer sentido. Padrão: **`caminho` — propósito (1-2 linhas)**.

## Raiz

- **`README.md`** — visão de produto, quickstart, endpoints, padrões.
- **`STUDY_GUIDE.md`** — este arquivo.
- **`Makefile`** — `make up / down / smoke / test / lint / obs-open / clean`.
- **`docker-compose.yml`** — 13 serviços (8 app + Kafka, ZK, MySQL, Postgres, Redis, ES + Prometheus, Grafana, Jaeger).
- **`test.sh`** — smoke test end-to-end (registra → cria pedido → paga → verifica PAID).
- **`.gitignore`** — Python/JVM/Go artifacts.
- **`pyproject.toml`** — config raiz do ruff (regras E,W,F,I,B,UP).
- **`.trivyignore`** — CVEs aceitos (vazio até decidir baseline).

## `.github/workflows/`

- **`ci.yml`** — pipelines paralelas: Python (ruff + pytest+coverage), Java (maven), Kotlin (gradle), Go (build+test+race), compose-config, Trivy fs (CRITICAL=fail) + config (advisory).

## `infra/`

- **`mysql/init.sql`** — schema fallback (Flyway é a fonte de verdade nos JVM).
- **`postgres/init.sql`** — products, payments, idempotency_keys, notifications.
- **`redis/redis.conf`** — bind, maxmemory 256mb, allkeys-lru.
- **`kafka/topics.sh`** — cria todos os tópicos de aplicação + DLQ (1 partição, 30d retenção).
- **`elasticsearch/mappings.json`** — settings com analyzer customizado.
- **`prometheus/prometheus.yml`** — scrape configs para os 8 serviços.
- **`grafana/provisioning/datasources/prometheus.yml`** — Prometheus + Jaeger pré-configurados.
- **`grafana/provisioning/dashboards/dashboards.yml`** — provider para auto-load.
- **`grafana/dashboards/melisim-overview.json`** — dashboard com 5 painéis (RPS por serviço, p95 latency, availability, Kafka events/sec, outbox state).

## `api-gateway/` (Python/FastAPI)

- **`Dockerfile`** — Python 3.11 slim, requirements, healthcheck.
- **`requirements.txt`** — fastapi, uvicorn, httpx, jose, passlib, prometheus-client, opentelemetry, redis, pytest.
- **`.dockerignore`** — exclui `__pycache__`, `tests/`, `.git/`.
- **`main.py`** — FastAPI app, monta middlewares na ordem certa (Correlation → Auth → RateLimit → Prometheus → CORS), `/health/live`, `/health/ready` (verifica users-service), `/metrics`, lifespan com httpx singleton.
- **`observability.py`** — wiring OpenTelemetry (TracerProvider + OTLP HTTP exporter + FastAPIInstrumentor + HTTPXInstrumentor).
- **`middleware/auth.py`** — `AuthMiddleware`. Valida JWT exceto para `PUBLIC_PATHS` (login, register, products GET).
- **`middleware/correlation.py`** — `CorrelationIdMiddleware` + `RequestIdLogFilter` para o JSON log format.
- **`middleware/cors.py`** — wrapper `setup_cors`.
- **`middleware/rate_limiter.py`** — sliding window in-memory (fallback dev).
- **`middleware/rate_limiter_redis.py`** — Lua-based sliding window distribuído.
- **`middleware/metrics.py`** — `PrometheusMiddleware` + `metrics_endpoint()`. Counter `http_requests_total{method,path,status}` + Histogram `http_request_duration_seconds`.
- **`routes/router.py`** — proxy reverso. `_proxy()` repassa método/headers/body/query, **propaga `x-request-id`**. Mapeia `/api/v1/*` para upstreams via env vars.
- **`tests/test_gateway.py`** — health, auth missing, auth invalid, rate limit, valid token bypass.

## `users-service/` (Java/Spring Boot)

- **`pom.xml`** — spring-boot-starter-{web,data-jpa,validation,security,actuator}, mysql-connector-j, jjwt, micrometer-registry-prometheus, opentelemetry-exporter-otlp, flyway-core+mysql.
- **`Dockerfile`** — multi-stage (maven build → temurin-17-jre-alpine).
- **`src/main/resources/application.yml`** — server graceful shutdown, datasource Hikari (pool=20, leak-detect=30s), JPA `ddl-auto: validate`, Flyway, actuator com prometheus + health probes, OTLP tracing, JWT secret.
- **`src/main/resources/db/migration/V1__init_users.sql`** — tabela users.
- **`src/main/java/com/melisim/users/UsersApplication.java`** — `@SpringBootApplication`.
- **`model/User.java`** — `@Entity`, `@PrePersist/@PreUpdate` para timestamps, enum UserType.
- **`model/UserType.java`** — BUYER, SELLER.
- **`repository/UserRepository.java`** — Spring Data JPA, `findByEmail`, `existsByEmail`.
- **`dto/UserRequest.java`** — `@Email`, `@Size(min=8)` validations.
- **`dto/UserResponse.java`** — sem password_hash, com factory `from(User)`.
- **`dto/LoginRequest.java`** + **`TokenResponse.java`** — auth.
- **`exception/UserNotFoundException.java`** + **`EmailAlreadyExistsException.java`** + **`InvalidCredentialsException.java`** — domain exceptions.
- **`exception/GlobalExceptionHandler.java`** — `@RestControllerAdvice` mapeando para HTTP status corretos.
- **`config/SecurityConfig.java`** — `BCryptPasswordEncoder` bean + `SecurityFilterChain` stateless permitAll (filtro real é JWT no gateway).
- **`config/CorrelationIdFilter.java`** — filter de request com `MDC.put("request_id", ...)`.
- **`service/UserService.java`** — register (BCrypt encode + check duplicate), login, get/update/delete.
- **`service/JwtService.java`** — emite JWT HS256 com claims `email`, `role`.
- **`controller/UserController.java`** — endpoints REST.
- **`src/test/java/.../UserServiceTest.java`** — JUnit 5 + Mockito (5 testes).
- **`src/test/java/.../UserControllerTest.java`** — `@WebMvcTest` (3 testes).

## `products-service/` (Go)

- **`go.mod`** + **`go.sum`** — chi, pgx/v5, redis/go-redis/v9, segmentio/kafka-go, prometheus/client_golang, google/uuid.
- **`Dockerfile`** — multi-stage (golang:1.22-alpine → alpine:3.19), HEALTHCHECK.
- **`cmd/main.go`** — wiring (repo, cache, publisher, service, handler), middlewares chi (RequestID, Recoverer, CorrelationID, Metrics, StructuredLogger), routes, graceful shutdown.
- **`internal/model/product.go`** — Product struct + Create/Update/UpdateStock requests + StockUpdated/ProductCreated events.
- **`internal/repository/product_repository.go`** — pgxpool com config tuning (MaxConns=25, MinConns=5, MaxConnLifetime=30min, HealthCheckPeriod=1min). CRUD + paginação. `ApplyStockDelta` com guard SQL `WHERE stock + $1 >= 0`. `LowStock` para o stock-monitor.
- **`internal/cache/cache.go`** — Redis JSON helpers (GetJSON/SetJSON/Del). Erro tipado `ErrMiss`.
- **`internal/events/publisher.go`** — `KafkaPublisher` (interface `Publisher`), writers por tópico, AllowAutoTopicCreation. Fail-soft (loga, não bloqueia request).
- **`internal/service/product_service.go`** — interface `Store` + `Cache` injetáveis. List/Get com cache-aside + invalidação targetada em writes.
- **`internal/handler/product_handler.go`** — HTTP handlers, depende só de uma interface (testável). Status codes corretos (201, 204, 400, 404, 409 quando estoque iria negativo).
- **`internal/observability/observability.go`** — Counter/Histogram Prometheus + middleware Metrics (usa chi route pattern para evitar explosão de cardinality em `/products/42`) + middleware CorrelationID.
- **`internal/middleware/logging.go`** — structured log JSON com método/path/status/duration_ms.
- **`tests/product_handler_test.go`** — table tests com fakeSvc satisfazendo a interface.
- **`.dockerignore`** — exclui tests, .git, binaries.

## `orders-service/` (Kotlin/Spring Boot)

- **`build.gradle.kts`** — Spring Boot, Kotlin 1.9, AOP, Kafka, Resilience4j Spring Boot 3, Resilience4j Reactor, Flyway, Micrometer Prometheus + tracing OTel, mockk + springmockk.
- **`Dockerfile`** — multi-stage (gradle:8.5 → temurin-17-jre-alpine).
- **`src/main/resources/application.yml`** — Tomcat threads=200, Hikari pool=20, Flyway, Kafka producer (acks=all, idempotente, snappy, linger=10ms, batch=32KB) + consumer (cooperative-sticky, max-poll=100, manual ack), listener concurrency=3, actuator com circuitbreakers health, Resilience4j (CB+Retry+TimeLimiter+Bulkhead).
- **`src/main/resources/db/migration/V1__init_orders.sql`** — tabela orders.
- **`src/main/resources/db/migration/V2__outbox.sql`** — tabela outbox_events com índices.
- **`src/main/kotlin/com/melisim/orders/OrdersApplication.kt`** — `@SpringBootApplication` + `@EnableKafka`.
- **`model/Order.kt`** — `@Entity` com `@PrePersist`/`@PreUpdate`.
- **`model/OrderStatus.kt`** — enum + `canTransitionTo` state machine.
- **`repository/OrderRepository.kt`** — JpaRepository + `findByBuyerId`.
- **`dto/OrderDTO.kt`** — `CreateOrderRequest` (com Bean Validation), `OrderResponse.from(Order)`, `UpdateStatusRequest`.
- **`client/ProductsClient.kt`** — RestClient com timeouts explícitos (connect 2s, read 3s), `@CircuitBreaker(fallback)` + `@Retry`. Lança `ProductNotFoundException`/`InsufficientStockException`/`ProductsUnavailableException`.
- **`outbox/OutboxEvent.kt`** — `@Entity`, payload é `JdbcTypeCode(SqlTypes.JSON)`. Status PENDING/SENT/FAILED.
- **`outbox/OutboxRepository.kt`** — `lockPending` com `@Lock(PESSIMISTIC_WRITE)` + `deleteSentBefore` `@Modifying`.
- **`outbox/OutboxPublisher.kt`** — `@Transactional(MANDATORY)` — só funciona dentro de tx existente, força chamador a estar transacional.
- **`outbox/OutboxPublisherWorker.kt`** — `@Scheduled(fixedDelay)`, pipeline send (todas as futures em paralelo, depois `.get()`), gauge de pendentes, timer de drain duration.
- **`outbox/OutboxCleanupWorker.kt`** — `@Scheduled(cron)` noturno, deleta SENT > N dias.
- **`event/OrderCreatedInternalEvent.kt`** — Spring application event, distinto do evento Kafka.
- **`event/PaymentEventConsumer.kt`** — `@KafkaListener` para `payment-confirmed`/`payment-failed`, atualiza status do pedido.
- **`service/OrderService.kt`** — `@Transactional` create. Salva + outbox.stage + events.publishEvent (após commit).
- **`service/OrderSideEffects.kt`** — `@TransactionalEventListener(AFTER_COMMIT)` chama productsClient.decrementStock fora da tx.
- **`controller/OrderController.kt`** — endpoints + `@ExceptionHandler` para domain exceptions.
- **`config/CorrelationIdFilter.kt`** — `OncePerRequestFilter` + MDC.
- **`src/test/kotlin/.../OrderServiceTest.kt`** — 5 testes mockk (cria stage outbox + publishEvent; rejeita estoque insuficiente; transição inválida; not-found; transição válida).

## `payments-service/` (Python/FastAPI)

- **`requirements.txt`** — fastapi, sqlalchemy[asyncio], asyncpg, aiokafka, prometheus-client, opentelemetry, aiosqlite (testes), pytest.
- **`Dockerfile`** — Python 3.11-slim com healthcheck.
- **`db.py`** — `create_async_engine` com pool tuning (size=10, overflow=20, pre_ping, recycle=1800, timeout=10).
- **`main.py`** — FastAPI app, lifespan (cria tabelas, start kafka producer), `/health/live`, `/health/ready` com `SELECT 1`, monta observability.
- **`observability.py`** — middleware Prometheus + correlation + setup_tracing OTLP + counters de events.
- **`models/payment.py`** — `Base = declarative_base()`, `PaymentORM` + `PaymentCreateRequest`/`PaymentResponse` Pydantic.
- **`models/payment_status.py`** — enum PaymentStatus + PaymentMethod.
- **`models/idempotency.py`** — `IdempotencyKey` ORM (unique key, fingerprint, status, body, created_at).
- **`services/payment_service.py`** — `_validate_request`, `_simulate_processing` (deterministic), `create_payment` (PROCESSING → CONFIRMED/FAILED, publica Kafka).
- **`services/idempotency_service.py`** — `fingerprint(body)` SHA-256 do JSON canônico, `get_stored`, `store` com IntegrityError handling para race.
- **`events/payment_events.py`** — `KafkaPublisher` async (aiokafka), fail-soft, singleton `publisher`.
- **`routes/payment_routes.py`** — `POST /payments` com Idempotency-Key handling, GET por ID, GET por order_id.
- **`tests/test_payments.py`** — 5 testes (confirmed, failed acima de 100k, invalid method, negative amount, get missing).
- **`tests/test_idempotency.py`** — 4 testes (fingerprint estável, fingerprint muda, store/retrieve, retrieve missing).

## `notifications-service/` (Python/FastAPI)

- **`requirements.txt`** — fastapi, sqlalchemy, asyncpg, aiokafka, jinja2, prometheus-client, opentelemetry.
- **`main.py`** — FastAPI app + engine SQLAlchemy + lifespan que sobe consumer task, install observability, endpoint history.
- **`observability.py`** — idêntico ao do payments (poderia ser shared).
- **`models/notification.py`** — `NotificationORM` + `NotificationResponse`.
- **`services/email_service.py`** — Jinja2 environment, `render(template, **ctx)` + `send_email` (printa no console — simulação).
- **`services/push_service.py`** — `send_push` simulado.
- **`services/notification_service.py`** — handlers por tópico (`dispatch_order_created`, `dispatch_payment_confirmed`, `dispatch_payment_failed`, `dispatch_stock_alert`) + `record` (escreve no DB) + `history`.
- **`consumers/notification_consumer.py`** — `run_consumer` com retry interno (3x backoff exp), DLQ producer separado, manual offset commit.
- **`templates/order_confirmed.html`** + **`payment_confirmed.html`** + **`payment_failed.html`** + **`stock_alert.html`** — Jinja2.
- **`tests/test_notifications.py`** — 4 testes async com SQLite in-memory.

## `search-service/` (Python/FastAPI)

- **`requirements.txt`** — fastapi, elasticsearch[async], aiokafka, prometheus, opentelemetry.
- **`main.py`** — FastAPI app, lifespan ensure_index + start consumer task + `/health/ready` com ES ping.
- **`observability.py`** — idem.
- **`services/search_service.py`** — classe `SearchService`. `_MAPPINGS` com analyzer + completion field. `ensure_index`, `index_product`, `search` (bool query com multi_match + filters), `suggest` (completion suggester).
- **`routes/search_routes.py`** — `GET /search` + `GET /search/suggestions`.
- **`consumers/product_consumer.py`** — consume `product-created` (indexa) + `stock-updates` (update parcial via doc).
- **`tests/test_search.py`** — 5 testes mockando `client.search`/`client.index`.

## `stock-monitor/` (Go)

- **`go.mod`** — segmentio/kafka-go, prometheus/client_golang.
- **`Dockerfile`** — multi-stage Go.
- **`cmd/main.go`** — Job ticker (60s), HTTP server lateral só para `/metrics` + `/health` (porta 8099). Counters Prometheus (ticks_total, low_count, alerts_published).
- **`internal/model/stock_alert.go`** — Product + StockAlert.
- **`internal/monitor/stock_monitor.go`** — `Client.FetchAll` paginando `GET /products`, `LowStock` filtra `stock < threshold`.
- **`internal/alerter/alerter.go`** — `Alerter.Publish` Kafka + `LogAudit` no formato `error_code,YYYY-MM-DD,server_id,endpoint`.
- **`tests/stock_monitor_test.go`** — 4 testes (filtro, vazio, paginação, stop em vazio).

---

# Parte VI — Como Apresentar na Entrevista

## Elevator pitch

### 30 segundos
> "MeliSim é um marketplace simulado nos moldes do Mercado Livre — 8 microserviços em 4 linguagens (Python, Java, Kotlin, Go), comunicando por REST e Kafka. Implementa padrões reais de plataforma: Outbox transacional para evitar dual-write, Idempotency-Key em pagamentos, Resilience4j com CB+Retry+Bulkhead nas chamadas síncronas, e DLQ para mensagens que não conseguem ser processadas. Observabilidade completa com Prometheus, Grafana e Jaeger, com correlation IDs propagados ponta a ponta. Sobe inteiro com `make up`."

### 2 minutos
Adicione:
- "Cada serviço foi escrito na linguagem que melhor encaixa: Go nos hot-paths de catálogo e no worker scheduled, Kotlin no orders porque o domínio é rico em transições de estado, Python nos serviços I/O-heavy."
- "O orders-service é o que mais demonstra senioridade: Outbox pattern (resolve dual-write), Resilience4j na chamada para products (CB + Retry + Bulkhead), e o decrementStock acontece em `@TransactionalEventListener(AFTER_COMMIT)` para não prender conexão durante HTTP."
- "Tudo passa por CI multi-linguagem com Trivy filesystem scan que falha em CRITICAL — supply chain security é cidadão de primeira classe."

### 5 minutos
Adicione:
- Walkthrough do fluxo de pedido (slide 1 do README)
- Demo: `make up`, abre Grafana, faz um pedido, mostra o trace no Jaeger, mostra o evento no outbox table
- Discussão de trade-offs: "Por que CQRS leve no search? Por que não Saga full?"

## Perguntas comuns + respostas modelo

### "Como o sistema garante consistência entre o pedido e o evento Kafka?"

> "Transactional Outbox. Inside a `@Transactional` method, eu insiro o pedido na tabela `orders` E o evento na tabela `outbox_events` — ambos commitam atomicamente ou rollback juntos. Um worker `@Scheduled` faz polling em PENDING com lock pessimista, manda pra Kafka em pipeline, marca como SENT. Garante at-least-once delivery; consumidores precisam ser idempotentes — usam `event_id` ou natural key (`order_id`)."

### "E se o orders-service cair entre o save e o evento?"

> "Não importa. A transação ainda não commitou; quando volta, JPA faz rollback. Nem o pedido, nem o outbox row existem. O cliente recebe 5xx, retenta — idealmente com Idempotency-Key se a API suportar (futuro: hoje só payments tem)."

### "Como você lida com poison messages no Kafka?"

> "Notifications consumer faz retry interno com backoff exponencial (200ms → 400ms → 800ms, max 3 tentativas). Se ainda falha, publica em `<topic>.dlq` com envelope rico (offset original, error type, timestamp), e commita o offset original para não bloquear a partição. DLQs têm 1 partição e 30 dias de retenção — são pra triagem manual, não throughput."

### "Como você descobre que um request específico falhou?"

> "Correlation ID. O gateway gera `X-Request-ID` (UUID4) na entrada, propaga em todos os headers downstream, coloca no MDC (Java/Kotlin) e contextvar (Python). Os logs JSON têm o campo `request_id`, e o OpenTelemetry adiciona como span attribute — então no Jaeger eu acho o trace, vejo todos os hops, e correlaciono com logs em Loki/CloudWatch."

### "Por que rate limiter em Redis e não in-memory?"

> "In-memory funciona pra uma instância. Quando escala horizontal — load balancer joga requests entre N gateways — cada um tem seu próprio counter, e o limite real fica N × o configurado. Redis com Lua script (sliding window via sorted set) dá uma fonte única de verdade. Se Redis cair, o limiter fail-open (libera): trade-off consciente, limiter caído ≠ gateway caído."

### "E se o sistema crescer 10x?"

> "Várias alavancas:
> 1. **Horizontal**: todos os serviços são stateless, escalam linear adicionando réplicas. Kafka particiona por chave (order_id), então consumers escalam até o número de partições.
> 2. **Caching**: Redis já está na frente de products GET. Próximo passo: cache de read do search-service.
> 3. **Outbox worker**: hoje uma instância faz polling. Com lock pessimista, dá pra ter N workers — eles competem mas não duplicam.
> 4. **DB**: read replicas pro Postgres em queries pesadas; sharding por seller_id se products crescer muito.
> 5. **Backpressure**: Kafka consumer com `max.poll.records` e concurrency tunável. Bulkhead no Resilience4j evita thundering herd em upstream lento.
> 6. **Search**: ES já é multi-shard ready. Hot/warm/cold se for histórico longo."

### "Por que não saga completa?"

> "É a próxima evolução natural. Hoje o fluxo `order-created → payment` tem rollback parcial: `payment-failed` move o pedido pra CANCELLED. Mas se eu adicionar shipping, fica claro que precisa um orquestrador de saga (ou choreographed via eventos) com compensações explícitas. Documentei isso na seção 'What's NOT here yet' do README — escolha consciente de escopo."

### "Como você testou tudo isso?"

> "Três camadas:
> - **Unit**: cada serviço tem 4-8 testes (pytest, JUnit/Mockito, MockK, Go testing). Mockam dependências externas.
> - **Smoke E2E**: `test.sh` sobe a stack e roda registro → cria 5 produtos → busca → cria pedido → paga → verifica PAID → mostra histórico de notificações. Cobre o fluxo principal.
> - **CI**: GitHub Actions roda lint (ruff enforced, golangci-lint), tests com cobertura, Trivy fs scan (CRITICAL=fail), compose config validation.
> O que falta: integration tests com Testcontainers — documentei como próximo passo."

## Demo plan (5 min ao vivo)

1. **`make up`** → todos containers up (~30s).
2. Abre `http://localhost:8000/docs` → mostra Swagger.
3. **`make smoke`** → roda end-to-end no terminal.
4. Abre **Grafana** → dashboard `MeliSim overview`. Mostra:
   - HTTP RPS por serviço
   - p95 latency
   - `melisim_events_published_total{event_type="order-created"}` subindo
   - `melisim_outbox_events{state="pending"}` indo pra zero
5. Abre **Jaeger** → seleciona `api-gateway` → clica em um trace → mostra os spans em árvore: gateway → orders → products (HTTP) + Kafka publish.
6. **MySQL CLI**: `SELECT * FROM outbox_events ORDER BY id DESC LIMIT 5;` — mostra rows SENT.

---

# Parte VII — Glossário

| Termo | Definição rápida |
|---|---|
| **Bounded context** | Pedaço do domínio com vocabulário próprio. Cada serviço aqui é um bounded context. |
| **CQRS** | Command Query Responsibility Segregation — write model separado do read model. Aqui: products (write) → search (read). |
| **Saga** | Sequência de transações locais com compensações para falhas. Não temos completo, mas o caminho está aberto. |
| **Outbox** | Padrão para resolver dual-write entre DB e broker. Implementado em orders. |
| **Idempotency** | Operação produz mesmo resultado se executada N vezes. Implementado em payments. |
| **Circuit Breaker** | Para de chamar um serviço caído depois de X% de falhas. Resilience4j. |
| **Bulkhead** | Limita concorrência por dependência. Uma upstream lenta não come todas as threads. |
| **DLQ** | Dead Letter Queue. Tópico para mensagens que falharam todos os retries. |
| **At-least-once** | Mensagem entregue 1+ vezes (pode duplicar). Padrão Kafka sem transações end-to-end. |
| **Exactly-once** | Sem duplicatas nem perdas. Caro de garantir; idempotência no consumer é o caminho prático. |
| **Eventual consistency** | Estado converge dado tempo. Trade-off do mundo distribuído. |
| **Cache aside** | App lê cache → miss → lê DB → escreve cache. Implementado em products. |
| **Liveness** | "Estou vivo?" — process responde. k8s reinicia se fail. |
| **Readiness** | "Posso receber tráfego?" — DB up, Kafka up. k8s tira do pool se fail. |
| **MDC** | Mapped Diagnostic Context (SLF4J). Onde correlation_id mora em Java/Kotlin. |
| **OTLP** | OpenTelemetry Protocol. Formato wire para enviar traces/metrics/logs. |
| **Sliding window (rate limit)** | Janela móvel — diferente de fixed window que tem cliffs nos minutos. |

---

**Fim.** Esse documento é vivo — quando adicionar Testcontainers, Saga, mTLS, atualize aqui. Se um entrevistador pedir pra explicar alguma parte específica, abra direto na seção e siga.
