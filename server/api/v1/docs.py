from __future__ import annotations

from fastapi import APIRouter, Query, status

from domain.community.docs_index import get_docs_index_service


router = APIRouter(tags=["docs"])
_service = get_docs_index_service()


@router.get("/docs/search", status_code=status.HTTP_200_OK)
def search_docs(q: str = Query(..., min_length=1)) -> dict:
    return {"query": q, "results": _service.search(q)}


@router.get("/docs/categories", status_code=status.HTTP_200_OK)
def list_categories() -> dict:
    return {"categories": _service.categories()}


@router.get("/docs/category/{category}", status_code=status.HTTP_200_OK)
def list_docs_by_category(category: str) -> dict:
    return {"category": category, "docs": _service.docs_in_category(category)}
