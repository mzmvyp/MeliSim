import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.search_service import SearchService


@pytest.mark.asyncio
async def test_search_returns_source_docs():
    svc = SearchService()
    fake_resp = {
        "hits": {
            "hits": [
                {"_source": {"id": 1, "title": "iPhone 15", "price": 7999.0}},
                {"_source": {"id": 2, "title": "iPhone 14", "price": 5999.0}},
            ]
        }
    }
    svc.client = MagicMock()
    svc.client.search = AsyncMock(return_value=fake_resp)

    results = await svc.search(q="iphone")
    assert len(results) == 2
    assert results[0]["title"] == "iPhone 15"


@pytest.mark.asyncio
async def test_search_empty_query_uses_match_all():
    svc = SearchService()
    svc.client = MagicMock()
    svc.client.search = AsyncMock(return_value={"hits": {"hits": []}})

    await svc.search(q="")
    body = svc.client.search.await_args.kwargs["body"]
    assert body["query"]["bool"]["must"][0] == {"match_all": {}}


@pytest.mark.asyncio
async def test_search_filters_price_range():
    svc = SearchService()
    svc.client = MagicMock()
    svc.client.search = AsyncMock(return_value={"hits": {"hits": []}})

    await svc.search(q="phone", min_price=100, max_price=500)
    body = svc.client.search.await_args.kwargs["body"]
    filters = body["query"]["bool"]["filter"]
    price_filter = next(f for f in filters if "range" in f)
    assert price_filter["range"]["price"] == {"gte": 100, "lte": 500}


@pytest.mark.asyncio
async def test_suggest_returns_options():
    svc = SearchService()
    svc.client = MagicMock()
    svc.client.search = AsyncMock(return_value={
        "suggest": {"title-suggest": [{"options": [{"text": "iphone"}, {"text": "ipad"}]}]}
    })
    out = await svc.suggest("ip")
    assert out == ["iphone", "ipad"]


@pytest.mark.asyncio
async def test_index_product_swallows_errors():
    svc = SearchService()
    svc.client = MagicMock()
    svc.client.index = AsyncMock(side_effect=RuntimeError("es down"))
    # Should not raise — indexing failures are logged.
    await svc.index_product({"id": 1, "title": "Book"})


@pytest.mark.asyncio
async def test_index_product_strict_raises():
    svc = SearchService()
    svc.client = MagicMock()
    svc.client.index = AsyncMock(side_effect=RuntimeError("es down"))
    with pytest.raises(RuntimeError, match="es down"):
        await svc.index_product({"id": 1, "title": "Book"}, strict=True)


@pytest.mark.asyncio
async def test_update_product_stock_strict_raises():
    svc = SearchService()
    svc.client = MagicMock()
    svc.client.update = AsyncMock(side_effect=RuntimeError("es down"))
    with pytest.raises(RuntimeError, match="es down"):
        await svc.update_product_stock(1, 5, strict=True)
