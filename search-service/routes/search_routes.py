from typing import Optional

from fastapi import APIRouter, Query

from services.search_service import service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query("", description="Full-text query"),
    category: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    size: int = Query(20, ge=1, le=100),
):
    items = await service.search(q=q, category=category, min_price=min_price, max_price=max_price, size=size)
    return {"query": q, "count": len(items), "items": items}


@router.get("/suggestions")
async def suggestions(
    q: str = Query(..., min_length=1, description="Prefix to complete"),
    size: int = Query(10, ge=1, le=50),
):
    return {"query": q, "suggestions": await service.suggest(q, size=size)}
