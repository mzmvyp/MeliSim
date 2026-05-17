"""Load Postgres-backed catalog into Elasticsearch on startup (HTTP, not Kafka)."""

from __future__ import annotations

import logging
import os

import httpx

from services.search_service import INDEX, service

log = logging.getLogger("search.catalog_bootstrap")


async def bootstrap_from_products_service() -> None:
    """Paginate GET /products and upsert each document. Kafka still handles live updates."""
    if os.getenv("SEARCH_BOOTSTRAP_CATALOG", "true").lower() not in ("1", "true", "yes"):
        log.info("catalog bootstrap disabled (SEARCH_BOOTSTRAP_CATALOG)")
        return

    base = os.getenv("PRODUCTS_SERVICE_URL", "http://localhost:8002").rstrip("/")
    url = f"{base}/products"
    page_size = 200
    page = 1
    total = 0

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                try:
                    r = await client.get(url, params={"page": str(page), "size": str(page_size)})
                except Exception as e:
                    log.warning("catalog bootstrap: GET failed page=%s: %s", page, e)
                    return
                if r.status_code != 200:
                    log.warning(
                        "catalog bootstrap: products-service returned %s page=%s body=%s",
                        r.status_code,
                        page,
                        (r.text or "")[:200],
                    )
                    return
                data = r.json()
                items = data.get("items") or []
                for raw in items:
                    if not isinstance(raw, dict) or raw.get("id") is None:
                        continue
                    await service.index_product(raw, strict=False, refresh=False)
                    total += 1
                if len(items) < page_size:
                    break
                page += 1
    finally:
        if total:
            try:
                await service.client.indices.refresh(index=INDEX)
            except Exception as e:
                log.warning("catalog bootstrap: refresh index failed: %s", e)
            log.info("catalog bootstrap: indexed %s products from %s", total, base)
