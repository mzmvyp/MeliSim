# MeliSim

Simulated Mercado Livre ecosystem — a polyglot microservices playground built for portfolio/study.

Eight services in four languages (Python, Java, Kotlin, Go) coordinate through REST and Kafka, backed by MySQL, PostgreSQL, Redis, and Elasticsearch. Spin it up, run the end-to-end script, and you get a full purchase flow: register → search → order → pay → notify.

---

## Architecture

```
                           ┌──────────────────────┐
   client  ─── HTTP ────►  │  api-gateway         │  Python / FastAPI  :8000
                           │  (JWT + rate limit)  │
                           └──────────┬───────────┘
                                      │
      ┌─────────────┬─────────────────┼──────────────────┬──────────────┐
      │             │                 │                  │              │
      ▼             ▼                 ▼                  ▼              ▼
┌──────────┐ ┌─────────────┐  ┌───────────────┐  ┌──────────────┐ ┌────────────┐
│  users   │ │  products   │  │    orders     │  │   payments   │ │   search   │
│  Java    │ │  Go         │  │    Kotlin     │  │   Python     │ │  Python    │
│  :8001   │ │  :8002      │  │    :8003      │  │   :8004      │ │  :8006     │
│  MySQL   │ │  Postgres   │  │    MySQL      │  │   Postgres   │ │  ES 8      │
│          │ │  Redis      │  │    Kafka      │  │   Kafka      │ │  Kafka     │
└──────────┘ └──────┬──────┘  └──────┬────────┘  └──────┬───────┘ └─────▲──────┘
                    │                │                  │               │
                    │ stock-updates  │ order-created    │ payment-*     │ product-*
                    ▼                ▼                  ▼               │
                 ┌────────────────────── Kafka ──────────────────────┐  │
                 └──────────────────────────┬────────────────────────┘  │
                                            │                           │
                                            ▼                           │
                                  ┌──────────────────┐                  │
                                  │  notifications   │  Python / FastAPI│
                                  │  :8005  Postgres │                  │
                                  └──────────────────┘                  │
                                                                        │
        stock-monitor (Go) ── polls /products every 60s ── publishes ───┘
                                       stock-alert
```

### Service map

| Service                | Language          | Port | Data                  | Purpose                                       |
|------------------------|-------------------|------|-----------------------|-----------------------------------------------|
| `api-gateway`          | Python/FastAPI    | 8000 | —                     | JWT auth, rate limit, reverse proxy           |
| `users-service`        | Java/Spring Boot  | 8001 | MySQL                 | Users + BCrypt + JWT issuer                   |
| `products-service`     | Go/chi            | 8002 | Postgres + Redis      | Catalog, cache, `stock-updates` producer      |
| `orders-service`       | Kotlin/Spring Boot| 8003 | MySQL + Kafka         | Orders lifecycle, consumes `payment-*`        |
| `payments-service`     | Python/FastAPI    | 8004 | Postgres + Kafka      | Simulated processor, `payment-*` producer     |
| `notifications-service`| Python/FastAPI    | 8005 | Postgres + Kafka      | Multi-topic consumer, email/push simulator    |
| `search-service`       | Python/FastAPI    | 8006 | Elasticsearch + Kafka | Indexes products, full-text + suggestions     |
| `stock-monitor`        | Go                | —    | Kafka                 | Periodic low-stock job, `stock-alert` producer|

### Kafka topics

- `order-created` — new order (producer: orders, consumer: notifications)
- `payment-confirmed` / `payment-failed` — payment outcome (producer: payments, consumers: orders, notifications)
- `stock-updates` — stock deltas (producer: products, consumer: search)
- `product-created` — new catalog entry (producer: products, consumer: search)
- `stock-alert` — low-stock warning (producer: stock-monitor, consumer: notifications)

---

## Quickstart

```bash
docker compose up --build
```

Wait until every service reports healthy (`docker compose ps`), then run:

```bash
./test.sh
```

The script walks the full purchase flow and prints what each stage returned.

### Useful endpoints

- API: http://localhost:8000
- Swagger (gateway): http://localhost:8000/docs
- Elasticsearch: http://localhost:9200
- Postgres: `localhost:5432` / user `melisim` / db `melisim`
- MySQL: `localhost:3306` / user `root` / db `melisim`

---

## Endpoints (through the gateway)

Everything below is relative to `http://localhost:8000/api/v1`.

| Method | Path                              | Purpose                                |
|--------|-----------------------------------|----------------------------------------|
| POST   | `/auth/register`                  | Create a user (buyer/seller)           |
| POST   | `/auth/login`                     | Returns JWT                            |
| GET    | `/users/{id}`                     | Fetch user (auth)                      |
| GET    | `/products`                       | List with pagination                   |
| GET    | `/products/{id}`                  | Fetch single                           |
| POST   | `/products`                       | Create (auth, seller)                  |
| PATCH  | `/products/{id}/stock`            | Adjust stock by delta                  |
| GET    | `/products/search?q=...`          | Full-text search                       |
| GET    | `/products/suggestions?q=...`     | Autocomplete                           |
| POST   | `/orders`                         | Create order (auth)                    |
| GET    | `/orders/{id}`                    | Fetch order                            |
| PATCH  | `/orders/{id}/status`             | Advance status (auth)                  |
| POST   | `/payments`                       | Process payment (auth)                 |
| GET    | `/payments/{id}`                  | Fetch payment                          |
| GET    | `/notifications/user/{id}`        | History (auth)                         |

All non-public routes require `Authorization: Bearer <jwt>`.

---

## Purchase flow (walk-through)

1. **Register + login** — buyer hits `POST /auth/register`, then `POST /auth/login` → receives JWT.
2. **Search** — `GET /products/search?q=iphone` → hits `search-service` (Elasticsearch).
3. **Create order** — `POST /orders` →
   - `orders-service` calls `products-service` over HTTP to fetch price + stock.
   - Rejects with `400` if stock insufficient.
   - Persists order with status `CREATED`; calls `PATCH /products/{id}/stock` (negative delta).
   - Publishes `order-created` on Kafka.
4. **Notification** — `notifications-service` consumes `order-created` → renders `order_confirmed.html` → logs a simulated email + writes a row in `notifications`.
5. **Pay** — `POST /payments` → `payments-service` writes PROCESSING row, simulates 2s delay, decides CONFIRMED / FAILED, publishes `payment-confirmed` or `payment-failed`.
6. **Status update** — `orders-service` consumes `payment-confirmed` → moves the order to `PAID`. `notifications-service` consumes it too → sends receipt + push.
7. **Stock monitor** — every 60s `stock-monitor` pulls `/products`, filters `stock < 10`, emits one `stock-alert` per product, prints an audit line `ERR_LOW_STOCK,YYYY-MM-DD,server_id,/products`. `notifications-service` consumes the alert → notifies the seller.

---

## Why these tech choices

- **Python/FastAPI** for the gateway and the I/O-heavy services (payments, notifications, search). Fast to write, good async story, Pydantic makes request validation trivial.
- **Java/Spring Boot** for `users-service` — mature identity/security stack, BCrypt + JPA + JWT are boring-in-a-good-way here.
- **Go** for `products-service` and `stock-monitor` — the hot path of the catalog benefits from low-overhead concurrency; `stock-monitor` is a tight scheduled worker, Go's binary-without-runtime is ideal.
- **Kotlin/Spring Boot** for `orders-service` — domain model with invariants (status transitions, totals) reads cleanly in Kotlin while keeping Spring's ergonomics.
- **MySQL** for transactional user/order rows; **Postgres** for catalog and event-adjacent tables; **Redis** as a hot cache in front of product listings; **Kafka** because every interesting cross-service effect is an event; **Elasticsearch** for real search relevance + autocomplete.

---

## Running tests

Each service has unit tests. Run them inside the service folder:

```bash
# api-gateway / payments / notifications / search
cd <service> && pip install -r requirements.txt && pytest -q

# users-service
cd users-service && mvn -B test

# orders-service
cd orders-service && ./gradlew test

# products-service / stock-monitor
cd <service> && go test ./...
```

The GitHub Actions workflow at `.github/workflows/ci.yml` runs all of them in parallel on every push.

---

## Repo layout

See the tree at the top of the prompt that seeded this project, or just `ls`. Every service owns its `Dockerfile`, its tests, and a `main.*` entry point; shared infra lives under `infra/`.
