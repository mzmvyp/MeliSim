import logging
import os
from typing import Optional

from elasticsearch import AsyncElasticsearch

log = logging.getLogger("search.service")

INDEX = "products"

_MAPPINGS = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "melisim_text": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "id":          {"type": "long"},
            "seller_id":   {"type": "long"},
            "title":       {
                "type": "text", "analyzer": "melisim_text",
                "fields": {"suggest": {"type": "completion"}},
            },
            "description": {"type": "text", "analyzer": "melisim_text"},
            "category":    {"type": "keyword"},
            "price":       {"type": "double"},
            "stock":       {"type": "integer"},
        }
    },
}


class SearchService:
    def __init__(self, es_url: Optional[str] = None) -> None:
        url = es_url or os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        self.client = AsyncElasticsearch(hosts=[url])

    async def ensure_index(self) -> None:
        try:
            exists = await self.client.indices.exists(index=INDEX)
            if not exists:
                await self.client.indices.create(index=INDEX, body=_MAPPINGS)
                log.info("created elasticsearch index %s", INDEX)
        except Exception as e:
            log.warning("could not ensure index: %s", e)

    async def index_product(self, product: dict) -> None:
        pid = product.get("id")
        if pid is None:
            log.warning("product missing id, skipping index")
            return
        try:
            await self.client.index(index=INDEX, id=str(pid), document=product, refresh="wait_for")
            log.info("indexed product id=%s", pid)
        except Exception as e:
            log.warning("index failed id=%s: %s", pid, e)

    async def search(
        self,
        q: str = "",
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        size: int = 20,
    ) -> list[dict]:
        must: list[dict] = []
        filters: list[dict] = []

        if q.strip():
            must.append({
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "description"],
                    "fuzziness": "AUTO",
                }
            })
        else:
            must.append({"match_all": {}})

        if category:
            filters.append({"term": {"category": category}})
        if min_price is not None or max_price is not None:
            rng: dict[str, float] = {}
            if min_price is not None:
                rng["gte"] = min_price
            if max_price is not None:
                rng["lte"] = max_price
            filters.append({"range": {"price": rng}})

        body = {"query": {"bool": {"must": must, "filter": filters}}, "size": size}
        try:
            resp = await self.client.search(index=INDEX, body=body)
        except Exception as e:
            log.warning("search failed: %s", e)
            return []
        return [h["_source"] for h in resp["hits"]["hits"]]

    async def suggest(self, q: str, size: int = 10) -> list[str]:
        if not q.strip():
            return []
        body = {
            "size": 0,
            "suggest": {
                "title-suggest": {
                    "prefix": q,
                    "completion": {"field": "title.suggest", "size": size},
                }
            },
        }
        try:
            resp = await self.client.search(index=INDEX, body=body)
        except Exception as e:
            log.warning("suggest failed: %s", e)
            return []
        options = resp.get("suggest", {}).get("title-suggest", [{}])[0].get("options", [])
        return [opt["text"] for opt in options]

    async def close(self) -> None:
        await self.client.close()


service = SearchService()
