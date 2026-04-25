# MeliSim

Simulated Mercado Livre ecosystem — a polyglot, event-driven microservices playground built as a portfolio piece.

Eight services in four languages (Python, Java, Kotlin, Go) coordinate through REST and Kafka, backed by MySQL, PostgreSQL, Redis, and Elasticsearch, and observed end-to-end with Prometheus, Grafana, and Jaeger.

---

## What's here (and why it matters)

This is not a toy CRUD. The design includes the patterns you'd expect in a real distributed marketplace:

| Concern | How it's solved |
|---|---|
| **Observability** | Prometheus metrics + Grafana dashboard + Jaeger traces + correlation IDs (`X-Request-ID`) propagated across every service |
| **Resilience** | Resilience4j on the `orders → products` HTTP client: circuit breaker (50% failure / 20-call window), exponential-backoff retry, explicit connect/read timeouts |
| **Reliable event publishing** | **Transactional Outbox** in `orders-service` — Kafka events are written to an `outbox_events` table in the same DB tx as the order, then shipped asynchronously by a polling worker. No dual-write hazard. |
| **Idempotency** | `POST /payments` accepts `Idempotency-Key`. Same key + same body → replay the original response; same key + different body → 422. Clients can safely retry timed-out requests without double-charging. |
| **Schema migrations** | Flyway in every JVM service (`V1__`, `V2__` …). `ddl-auto: validate`. No more "Hibernate invents my schema." |
| **Health model** | `/health/live` (is the process up?) vs `/health/ready` (can the process actually serve traffic? — DB ping, upstream ping, ES ping). Spring services expose Spring Boot Actuator `liveness` and `readiness` probes. |
| **Graceful shutdown** | Every service honours SIGTERM: drains in-flight requests, stops Kafka consumers, closes DB pools. |
| **Security on CI** | Trivy filesystem + config scan on every PR (advisory mode while maintaining a baseline), plus Ruff + golangci-lint gates in CI. |
| **Caching** | Redis TTL cache in front of `GET /products` with targeted invalidation on writes |
| **Rate limiting** | Redis-backed sliding window per IP at the gateway when `REDIS_URL` is set (Lua + atomic ZSET); in-memory fallback for local dev without Redis |
| **Dead-letter queues (DLQ)** | `notifications-service` and `search-service` publish poison/failed messages to `<topic>.dlq` after bounded retries; `infra/kafka/topics.sh` creates every DLQ topic |
| **Order side-effects** | Stock decrement runs **after commit** (`OrderSideEffects` + Spring event) so the DB transaction is not held during HTTP to `products-service` |

---

## Architecture

```
                                ┌──────────────────────┐
   client  ──────── HTTP ────▶  │  api-gateway        │  Python/FastAPI  :8000
                                │  JWT + rate-limit   │
                                │  correlation id     │
                                └─────────┬───────────┘
                                          │  (X-Request-ID propagated)
   ┌──────────────┬────────────────┬──────┼──────────────┬────────────────┐
   │              │                │      │              │                │
   ▼              ▼                ▼      ▼              ▼                ▼
┌────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ users  │  │  products   │  │   orders    │  │   payments   │  │   search     │
│ Java   │  │  Go         │  │   Kotlin    │  │   Python     │  │   Python     │
│ :8001  │  │  :8002      │  │   :8003     │  │   :8004      │  │   :8006      │
│ MySQL  │  │  Postgres   │  │   MySQL     │  │   Postgres   │  │   ES 8       │
│ Flyway │  │  Redis      │  │   Flyway    │  │   Idempot.   │  │   Kafka      │
│ JWT    │  │  Kafka      │  │   Outbox +  │  │   Kafka      │  │              │
│        │  │             │  │   Resil4j   │  │              │  │              │
└────────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └──────▲───────┘
                   │                │                │                 │
                   │ stock-updates  │ order-created  │ payment-*       │ product-*
                   ▼                ▼                ▼                 │
             ┌────────────────── Kafka ──────────────────────────────┐ │
             └──────────────────────┬────────────────────────────────┘ │
                                    │                                  │
                                    ▼                                  │
                         ┌──────────────────┐                          │
                         │  notifications   │  Python/FastAPI          │
                         │  :8005  Postgres │                          │
                         └──────────────────┘                          │
                                                                       │
        stock-monitor (Go) ─── polls /products every 60s ── publishes ─┘
                                       stock-alert

                 ─── Observability plane ────────────────────────
                 Prometheus :9090  ──▶ Grafana :3000 (MeliSim overview)
                 Jaeger :16686  (traces from every HTTP service)
```

### Service map

| Service | Language | Port | Data | Purpose |
|---|---|---|---|---|
| `api-gateway` | Python/FastAPI | 8000 | — | JWT, rate limit, reverse proxy, correlation IDs |
| `users-service` | Java/Spring Boot | 8001 | MySQL | Users + BCrypt + JWT issuer (Flyway) |
| `products-service` | Go/chi | 8002 | Postgres + Redis | Catalog, cache, `stock-updates` producer |
| `orders-service` | Kotlin/Spring Boot | 8003 | MySQL + Kafka | Order lifecycle, **Resilience4j**, **Outbox** |
| `payments-service` | Python/FastAPI | 8004 | Postgres + Kafka | Simulated processor, **idempotent** |
| `notifications-service` | Python/FastAPI | 8005 | Postgres + Kafka | Multi-topic consumer, email/push sim |
| `search-service` | Python/FastAPI | 8006 | ES + Kafka | Full-text + autocomplete, indexes via events |
| `stock-monitor` | Go | 8099 (metrics) | Kafka | Periodic low-stock, `stock-alert` producer |
| **`prometheus`** | — | 9090 | — | Scrapes every `/metrics` endpoint |
| **`grafana`** | — | 3000 | — | Pre-provisioned dashboard + datasources |
| **`jaeger`** | — | 16686 | — | OTLP/HTTP collector + UI |

### Kafka topics

- `order-created` — producer: orders (via outbox); consumers: notifications
- `payment-confirmed` / `payment-failed` — producer: payments; consumers: orders, notifications
- `stock-updates` — producer: products; consumer: search
- `product-created` — producer: products; consumer: search
- `stock-alert` — producer: stock-monitor; consumer: notifications

**DLQ topics** (created by `infra/kafka/topics.sh`, 1 partition, 30-day retention):  
`order-created.dlq`, `payment-confirmed.dlq`, `payment-failed.dlq`, `stock-alert.dlq`, `product-created.dlq`, `stock-updates.dlq` — used when a consumer exhausts retries or JSON parsing fails; envelope includes original topic/partition/offset, payload, and error.

---

## Quickstart

```bash
make up        # build + run the full stack (13 containers)
make smoke     # end-to-end test walk-through
make obs-open  # open Grafana, Prometheus, Jaeger in the browser
```

or plain compose:

```bash
docker compose up --build -d
./test.sh
```

### CI status (current branch)

- Latest CI passes after fixing Python import-order lint issues and missing `api-gateway` runtime deps (`prometheus-client`, `redis`, OpenTelemetry packages).
- Trivy action uses `aquasecurity/trivy-action@v0.36.0` (working tag).
- GitHub still shows Node.js 20 deprecation annotations for some actions; these are warnings, not build failures.

### Ports & what each one shows

| URL | What you'll see |
|---|---|
| http://localhost:8000/docs | **Gateway Swagger** — every public route, `Try it out`-able |
| http://localhost:3000 | **Grafana** — open dashboard *MeliSim overview* (RPS, p95 latency, service availability, Kafka events/sec, outbox state) |
| http://localhost:9090 | **Prometheus** — raw metrics, `Status → Targets` shows whether every service is being scraped |
| http://localhost:16686 | **Jaeger** — pick `api-gateway` in the service dropdown to see end-to-end traces of a request hopping through 3-4 services |
| http://localhost:9200 | Elasticsearch HTTP (debug indexed products) |
| http://localhost:8002/metrics | products-service Prometheus exposition format |
| http://localhost:8001/actuator/prometheus | users-service via Spring Actuator |

> ⚠️ **This is a lab project.** Defaults like `admin/admin` for Grafana, anonymous Viewer access, hardcoded `JWT_SECRET` in `docker-compose.yml`, and Elasticsearch with `xpack.security.enabled=false` are deliberate to make the stack one-command runnable. **Do not deploy as-is to anything reachable from the internet.** Production checklist: external secrets manager (Vault/Doppler), Grafana SSO, real TLS termination, mTLS between services, and the Kafka cluster sized + ACL'd properly.

---

## Key patterns explained

### Transactional Outbox (orders-service)

The problem it solves: you can't atomically write to your DB **and** publish to Kafka. If you commit first and then the broker is down, you've got orders with no events; if you publish first and the commit fails, you've got ghost events.

The fix: inside the same JPA transaction that saves the order row, stage the event in an `outbox_events` table. After commit, a separate `@Scheduled` worker (`OutboxPublisherWorker`) polls PENDING rows **under a pessimistic lock**, ships them to Kafka, then marks them SENT. Failures increment `attempts`; after 10 tries the row goes FAILED and is surfaced as a Grafana gauge.

Files:
- `orders-service/src/main/kotlin/com/melisim/orders/outbox/` — entity, repo, publisher, worker
- `orders-service/src/main/resources/db/migration/V2__outbox.sql`

### Resilience4j (orders-service → products-service)

`ProductsClient` is decorated with `@CircuitBreaker(name="products")` + `@Retry(name="products")`. Tuning lives in `application.yml` under `resilience4j:`. When products-service misbehaves, the CB opens after 50% failure rate in a 20-call window and short-circuits fast for 10s before going half-open.

A fallback method converts raw `IOException` / timeouts into a domain `ProductsUnavailableException` so the controller returns a clean 503 instead of a leaky stack trace.

### Idempotency (payments-service)

`POST /payments` inspects the `Idempotency-Key` header and hashes the canonical JSON body (`fingerprint`). Four cases:

1. No key → normal processing.
2. Key + never seen → process, store `(key, fingerprint, response)` in `idempotency_keys`.
3. Key + same fingerprint → replay the stored response (`Idempotent-Replayed: true`).
4. Key + different fingerprint → `422 Unprocessable Entity`.

Files:
- `payments-service/models/idempotency.py`
- `payments-service/services/idempotency_service.py`
- `payments-service/routes/payment_routes.py`

### Observability trio

- **Metrics**: every HTTP service exposes `/metrics` (Prometheus). Spring services go through Micrometer; Python services use `prometheus-client`; Go services use `prometheus/client_golang`. Request counters + latency histograms + custom `melisim_events_published_total` / `melisim_outbox_events{state}`.
- **Traces**: OpenTelemetry SDK in Python services, Micrometer Tracing + OTel exporter in Spring. All point at `http://jaeger:4318/v1/traces`.
- **Correlation IDs**: gateway mints/propagates `X-Request-ID`; each service adds it to MDC (Spring) or a request-scoped contextvar (Python), so logs across services share a request id.

### Deep health checks

Every service has both `/health/live` (process responsiveness) and `/health/ready` (can I actually handle traffic? — DB `SELECT 1`, ES ping, upstream ping). Kubernetes-ready.

---

## Purchase flow (walk-through)

1. **Register + login** — buyer → `POST /auth/register`, `POST /auth/login` → JWT.
2. **Search** — `GET /products/search?q=iphone` → `search-service` (Elasticsearch).
3. **Create order** — `POST /orders`:
   - `orders-service` calls `GET /products/{id}` through Resilience4j (CB + retry).
   - Validates stock.
   - Persists the order **and** stages `order-created` in `outbox_events` — same tx.
   - The outbox worker picks it up and publishes to Kafka.
4. **Notification** — `notifications-service` consumes `order-created` → renders `order_confirmed.html` → logs an email + writes a `notifications` row.
5. **Pay** — `POST /payments` (with `Idempotency-Key: <uuid>`) → `payments-service` simulates a 2s processor → publishes `payment-confirmed` or `payment-failed`.
6. **Status update** — `orders-service` consumes `payment-confirmed` → `PAID`. `notifications-service` consumes it too → receipt + push.
7. **Stock monitor** — every 60s → pulls `/products`, filters `stock < 10`, emits `stock-alert` per product. `notifications-service` notifies the seller.

---

## Repository layout

```
melisim/
├── docker-compose.yml         # 13 services: 8 app + 5 infra/obs
├── Makefile                   # make up / make smoke / make test / make obs-open
├── test.sh                    # end-to-end purchase walk-through
├── .github/workflows/ci.yml   # lint + test + Trivy per language
├── README.md
├── api-gateway/               # Python — JWT, rate limit, correlation, metrics
├── users-service/             # Java — BCrypt, JWT, Flyway
├── products-service/          # Go — Postgres/Redis/Kafka, /metrics
├── orders-service/            # Kotlin — Resilience4j + Outbox + Flyway
├── payments-service/          # Python — Idempotency-Key, async SQLAlchemy
├── notifications-service/     # Python — multi-topic Kafka consumer
├── search-service/            # Python — Elasticsearch indexing from events
├── stock-monitor/             # Go — scheduled job, /metrics
└── infra/
    ├── mysql/init.sql          # fallback schema (Flyway owns it in prod)
    ├── postgres/init.sql       # products, payments, idempotency_keys, notifications
    ├── prometheus/prometheus.yml
    ├── grafana/                # provisioned datasources + dashboard
    ├── kafka/topics.sh
    └── elasticsearch/mappings.json
```

---

## Running tests

```bash
make test        # runs pytest + mvn + gradle + go test across all 8 services
```

Or per service:

```bash
cd payments-service && pytest -q
cd orders-service && ./gradlew test
cd products-service && go test ./...
```

---

## What's deliberately NOT here (yet)

These would be the next round of improvements:

- **Integration tests with Testcontainers** — unit tests + the compose smoke test cover most of the risk for now.
- **Service mesh / mTLS between services** — the gateway checks JWT; internal hops trust the network.
- **Kubernetes manifests / Helm charts** — docker-compose is the deployment model.
- **Saga compensation** — order/payment flow has no rollback path for partial failures beyond `payment-failed → CANCELLED`.
- **Contract tests** (Pact) between gateway and each service.

Each has a clear place to land when it's needed; nothing in the architecture blocks adding them.
