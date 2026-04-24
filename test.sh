#!/usr/bin/env bash
#
# MeliSim end-to-end smoke test.
# Runs through: register seller → register buyer → login → create 5 products →
# search → create order → pay → verify PAID → show notification history.
#
# Assumes: `docker compose up -d --build` has been executed and services are booting.
#
# From inside Docker (e.g. on Windows), services listen on the host — use:
#   docker run --rm -it -v "$PWD:/workspace" -w /workspace -e HOST=host.docker.internal alpine:3.19 \
#     sh -c "apk add --no-cache bash curl jq >/dev/null && bash ./test.sh"

set -euo pipefail

# Hostname for published ports (host.docker.internal from a container → host machine on Docker Desktop).
HOST="${HOST:-localhost}"
GATEWAY="${GATEWAY:-http://${HOST}:8000}"
MAX_WAIT="${MAX_WAIT:-180}"

say()   { printf "\n\033[1;36m>>> %s\033[0m\n" "$*"; }
fail()  { printf "\n\033[1;31m!!! %s\033[0m\n" "$*" >&2; exit 1; }

need() {
  command -v "$1" >/dev/null 2>&1 || fail "'$1' is required; please install it."
}

need curl
need jq

# ---------------------------------------------------------------------------
# 1. Wait for every service to be healthy via the gateway + direct health URLs.
# ---------------------------------------------------------------------------
wait_health() {
  local url="$1"; local label="$2"; local deadline=$(( $(date +%s) + MAX_WAIT ))
  while true; do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "  ✔ $label ready"
      return 0
    fi
    if (( $(date +%s) > deadline )); then
      fail "timeout waiting for $label ($url)"
    fi
    sleep 2
  done
}

say "waiting for services to come up"
wait_health "$GATEWAY/health"                              "api-gateway"
wait_health "http://${HOST}:8001/actuator/health"           "users-service"
wait_health "http://${HOST}:8002/health"                    "products-service"
wait_health "http://${HOST}:8003/actuator/health"           "orders-service"
wait_health "http://${HOST}:8004/health"                    "payments-service"
wait_health "http://${HOST}:8005/health"                    "notifications-service"
wait_health "http://${HOST}:8006/health"                    "search-service"

# ---------------------------------------------------------------------------
# 2. Register a seller + a buyer.
# ---------------------------------------------------------------------------
say "registering seller"
SELLER=$(curl -s -X POST "$GATEWAY/api/v1/auth/register" \
  -H 'content-type: application/json' \
  -d '{"name":"Alice Seller","email":"alice-seller@melisim.test","password":"super-secret-pw","userType":"SELLER"}')
echo "$SELLER" | jq .
SELLER_ID=$(echo "$SELLER" | jq -r '.id')

say "registering buyer"
BUYER=$(curl -s -X POST "$GATEWAY/api/v1/auth/register" \
  -H 'content-type: application/json' \
  -d '{"name":"Bob Buyer","email":"bob-buyer@melisim.test","password":"super-secret-pw","userType":"BUYER"}')
echo "$BUYER" | jq .
BUYER_ID=$(echo "$BUYER" | jq -r '.id')

# ---------------------------------------------------------------------------
# 3. Login buyer, capture JWT.
# ---------------------------------------------------------------------------
say "logging in as buyer"
LOGIN=$(curl -s -X POST "$GATEWAY/api/v1/auth/login" \
  -H 'content-type: application/json' \
  -d '{"email":"bob-buyer@melisim.test","password":"super-secret-pw"}')
echo "$LOGIN" | jq '{accessToken: (.accessToken[0:16] + "..."), expiresIn, user}'
JWT=$(echo "$LOGIN" | jq -r '.accessToken')
AUTH_HEADER=(-H "Authorization: Bearer $JWT")

# ---------------------------------------------------------------------------
# 4. Seller logs in + creates 5 products.
# ---------------------------------------------------------------------------
say "logging in as seller"
SELLER_LOGIN=$(curl -s -X POST "$GATEWAY/api/v1/auth/login" \
  -H 'content-type: application/json' \
  -d '{"email":"alice-seller@melisim.test","password":"super-secret-pw"}')
SELLER_JWT=$(echo "$SELLER_LOGIN" | jq -r '.accessToken')
SELLER_AUTH=(-H "Authorization: Bearer $SELLER_JWT")

say "creating 5 products"
for i in 1 2 3 4 5; do
  curl -s -X POST "$GATEWAY/api/v1/products" \
    "${SELLER_AUTH[@]}" \
    -H 'content-type: application/json' \
    -d "{\"seller_id\": $SELLER_ID, \"title\":\"MeliSim Gadget $i\",\"description\":\"Test product $i\",\"category\":\"electronics\",\"price\": $((50 + i * 10)).0, \"stock\": $((20 + i))}" \
    | jq '{id, title, price, stock}'
done

# ---------------------------------------------------------------------------
# 5. Search — Elasticsearch may take a tick to index.
# ---------------------------------------------------------------------------
say "searching 'gadget' (may be empty if index is still warming up)"
sleep 3
curl -s "$GATEWAY/api/v1/products/search?q=gadget" | jq '{query, count}'

# ---------------------------------------------------------------------------
# 6. Pick the first live product and create an order.
# ---------------------------------------------------------------------------
say "listing products via gateway"
LIST=$(curl -s "$GATEWAY/api/v1/products?page=1&size=10")
PRODUCT_ID=$(echo "$LIST" | jq -r '.items[0].id')
echo "  using product_id=$PRODUCT_ID"

say "creating order (buyer=$BUYER_ID, product=$PRODUCT_ID, qty=2)"
ORDER=$(curl -s -X POST "$GATEWAY/api/v1/orders" \
  "${AUTH_HEADER[@]}" \
  -H 'content-type: application/json' \
  -d "{\"buyerId\": $BUYER_ID, \"productId\": $PRODUCT_ID, \"quantity\": 2}")
echo "$ORDER" | jq .
ORDER_ID=$(echo "$ORDER" | jq -r '.id')
ORDER_TOTAL=$(echo "$ORDER" | jq -r '.totalAmount')

# ---------------------------------------------------------------------------
# 7. Pay the order.
# ---------------------------------------------------------------------------
say "paying order $ORDER_ID (total $ORDER_TOTAL via pix)"
PAYMENT=$(curl -s -X POST "$GATEWAY/api/v1/payments" \
  "${AUTH_HEADER[@]}" \
  -H 'content-type: application/json' \
  -d "{\"order_id\": $ORDER_ID, \"amount\": $ORDER_TOTAL, \"method\":\"pix\"}")
echo "$PAYMENT" | jq .

# ---------------------------------------------------------------------------
# 8. Wait for Kafka to propagate payment-confirmed to orders-service.
# ---------------------------------------------------------------------------
say "waiting for order to reach PAID"
for i in $(seq 1 20); do
  sleep 2
  STATUS=$(curl -s "$GATEWAY/api/v1/orders/$ORDER_ID" "${AUTH_HEADER[@]}" | jq -r '.status')
  echo "  attempt $i: status=$STATUS"
  if [ "$STATUS" = "PAID" ]; then
    break
  fi
done
if [ "$STATUS" != "PAID" ]; then
  fail "order $ORDER_ID did not reach PAID (last=$STATUS)"
fi

# ---------------------------------------------------------------------------
# 9. Notifications history for the buyer.
# ---------------------------------------------------------------------------
say "buyer notification history"
curl -s "$GATEWAY/api/v1/notifications/user/$BUYER_ID" "${AUTH_HEADER[@]}" \
  | jq '.[] | {event_type, subject, created_at}'

say "END-TO-END OK ✅"
