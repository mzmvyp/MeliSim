"""Bot de tráfego do Melisim.

Simula compradores que se registram (uma vez), logam, navegam pelo catálogo
de produtos via search-service e fazem pedidos + pagamentos. Cada ciclo
produz: 1 evento `order-created` (orders-service via outbox) + 1 evento
`payment-confirmed` ou `payment-failed` (payments-service) + atualização de
`stock` em `products` + alimenta `notifications`.

Variáveis de ambiente:
    BOT_API_BASE         URL base do api-gateway (default: http://api-gateway:8000)
    BOT_USERS            Numero de buyers simultaneos (default: 5)
    BOT_INTERVAL_SECONDS Intervalo entre ciclos (default: 8)
    BOT_PRODUCT_MAX_ID   Maior id de produto a sortear (default: 438)
"""

from __future__ import annotations

import os
import random
import string
import sys
import time
from dataclasses import dataclass

import httpx
from loguru import logger

API_BASE = os.environ.get("BOT_API_BASE", "http://api-gateway:8000").rstrip("/")
NUM_USERS = int(os.environ.get("BOT_USERS", "5"))
INTERVAL = float(os.environ.get("BOT_INTERVAL_SECONDS", "8"))
PRODUCT_MAX_ID = int(os.environ.get("BOT_PRODUCT_MAX_ID", "438"))
PASSWORD = os.environ.get("BOT_PASSWORD", "Botpwd123")
PAYMENT_METHODS = ["credit_card", "pix", "boleto"]


@dataclass
class Buyer:
    user_id: int
    email: str
    token: str


def _rand_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"bot+{suffix}@melisim.test"


def _register_or_login(client: httpx.Client) -> Buyer:
    email = _rand_email()
    name = f"Bot Buyer {email.split('@')[0]}"
    payload = {"name": name, "email": email, "password": PASSWORD, "userType": "BUYER"}

    r = client.post(f"{API_BASE}/api/v1/auth/register", json=payload, timeout=10.0)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"register failed: {r.status_code} {r.text[:200]}")

    r = client.post(
        f"{API_BASE}/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=10.0,
    )
    r.raise_for_status()
    data = r.json()
    return Buyer(
        user_id=int(data["user"]["id"]),
        email=email,
        token=data["accessToken"],
    )


def _browse(client: httpx.Client, *, query: str | None = None) -> None:
    """Faz uma busca / listagem de produtos (gera carga em search/products)."""
    try:
        if query:
            client.get(
                f"{API_BASE}/api/v1/products/search",
                params={"q": query, "size": 12},
                timeout=10.0,
            )
        else:
            client.get(
                f"{API_BASE}/api/v1/products",
                params={"page": 1, "size": 24},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        logger.warning(f"browse falhou: {exc}")


def _create_order(client: httpx.Client, buyer: Buyer) -> int | None:
    product_id = random.randint(1, PRODUCT_MAX_ID)
    quantity = random.randint(1, 3)
    headers = {"Authorization": f"Bearer {buyer.token}"}
    payload = {"buyerId": buyer.user_id, "productId": product_id, "quantity": quantity}
    try:
        r = client.post(
            f"{API_BASE}/api/v1/orders",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
        if r.status_code in (200, 201):
            data = r.json()
            order_id = int(data.get("id"))
            logger.info(
                f"order ok user={buyer.user_id} product={product_id} qty={quantity} -> order={order_id}"
            )
            return order_id
        logger.warning(
            f"order falhou user={buyer.user_id} product={product_id}: "
            f"{r.status_code} {r.text[:120]}"
        )
    except httpx.HTTPError as exc:
        logger.warning(f"order erro: {exc}")
    return None


def _pay(client: httpx.Client, *, buyer: Buyer, order_id: int, amount: float) -> None:
    method = random.choice(PAYMENT_METHODS)
    if random.random() < 0.30:
        amount = round(random.uniform(100_000, 250_000), 2)
    payload = {
        "order_id": order_id,
        "amount": amount,
        "method": method,
    }
    headers = {
        "Idempotency-Key": f"bot-{order_id}-{int(time.time())}",
        "Authorization": f"Bearer {buyer.token}",
    }
    try:
        r = client.post(
            f"{API_BASE}/api/v1/payments",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
        if r.status_code in (200, 201):
            data = r.json()
            logger.info(
                f"payment {data.get('status')} order={order_id} amount={amount} method={method}"
            )
        else:
            logger.warning(
                f"payment falhou order={order_id}: {r.status_code} {r.text[:120]}"
            )
    except httpx.HTTPError as exc:
        logger.warning(f"payment erro: {exc}")


def _get_order(client: httpx.Client, order_id: int) -> dict | None:
    try:
        r = client.get(f"{API_BASE}/api/v1/orders/{order_id}", timeout=10.0)
        if r.status_code == 200:
            return r.json()
    except httpx.HTTPError:
        pass
    return None


def main() -> int:
    logger.info(
        f"Bot iniciado base={API_BASE} users={NUM_USERS} interval={INTERVAL}s"
    )
    with httpx.Client() as client:
        # Aguarda gateway responder.
        for attempt in range(60):
            try:
                r = client.get(f"{API_BASE}/health", timeout=3.0)
                if r.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            logger.info(f"aguardando api-gateway... {attempt + 1}")
            time.sleep(2)
        else:
            logger.error("api-gateway nao respondeu, abortando")
            return 1

        # Cria pool de buyers.
        buyers: list[Buyer] = []
        for _ in range(NUM_USERS):
            try:
                buyers.append(_register_or_login(client))
                time.sleep(0.2)
            except Exception as exc:
                logger.warning(f"register falhou: {exc}")
        logger.info(f"buyers ativos: {len(buyers)}")

        if not buyers:
            logger.error("nenhum buyer registrado, abortando")
            return 1

        queries = [
            "iphone",
            "notebook",
            "tv",
            "fone",
            "tenis",
            "geladeira",
            "drone",
            "bike",
        ]

        cycle = 0
        while True:
            cycle += 1
            buyer = random.choice(buyers)
            _browse(client, query=random.choice(queries) if random.random() < 0.5 else None)
            order_id = _create_order(client, buyer)
            if order_id:
                # paga em ~85% dos casos
                if random.random() < 0.85:
                    order = _get_order(client, order_id)
                    amount = float(order.get("totalAmount", 0)) if order else 0.0
                    if amount <= 0:
                        amount = round(random.uniform(50, 800), 2)
                    _pay(client, buyer=buyer, order_id=order_id, amount=amount)
            time.sleep(INTERVAL + random.uniform(-2, 2))


if __name__ == "__main__":
    sys.exit(main())
