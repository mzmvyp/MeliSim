-- MeliSim Postgres schema: products + payments + notifications
CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(80),
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_seller ON products(seller_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    method VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- Idempotency-Key storage for POST /payments. Same key + same body → replay the
-- original response. Same key + different body → 422. Prevents double-charges
-- when clients retry a timed-out POST.
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id BIGSERIAL PRIMARY KEY,
    idempotency_key      VARCHAR(120) NOT NULL UNIQUE,
    endpoint             VARCHAR(120) NOT NULL,
    request_fingerprint  VARCHAR(64)  NOT NULL,
    response_status      INT          NOT NULL,
    response_body        TEXT         NOT NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    channel VARCHAR(30) NOT NULL,
    event_type VARCHAR(60) NOT NULL,
    subject VARCHAR(200),
    body TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_event ON notifications(event_type);

-- Seed products for demo
INSERT INTO products (seller_id, title, description, category, price, stock) VALUES
    (1, 'iPhone 15 Pro', 'Apple iPhone 15 Pro 256GB', 'electronics', 7999.00, 25),
    (1, 'Samsung Galaxy S24', 'Samsung Galaxy S24 Ultra', 'electronics', 6499.00, 15),
    (1, 'MacBook Air M3', 'Apple MacBook Air M3 13"', 'computers', 9999.00, 8)
ON CONFLICT DO NOTHING;
