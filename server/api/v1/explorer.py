from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from domain.explorer.export import ExportService
from domain.explorer.service import ChainExplorerService


router = APIRouter(prefix="/explorer", tags=["explorer"])
service = ChainExplorerService()
export_service = ExportService(explorer_service=service)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(UTC)


@router.get("/blocks", status_code=status.HTTP_200_OK)
def get_block_history(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict:
    return {"items": service.get_blocks(limit=limit, offset=offset), "limit": limit, "offset": offset}


@router.get("/blocks/{block_number}", status_code=status.HTTP_200_OK)
def get_block_details(block_number: int) -> dict:
    details = service.get_block_details(block_number=block_number)
    if details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="block_not_found")
    return details


@router.get("/players/{player_id}/history", status_code=status.HTTP_200_OK)
def get_player_history(player_id: str, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict:
    return {"items": service.get_player_history(player_id=player_id, limit=limit, offset=offset), "limit": limit, "offset": offset}


@router.get("/players/{player_id}/earnings", status_code=status.HTTP_200_OK)
def get_player_earnings(player_id: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    return {"items": service.get_player_earnings(player_id=player_id, start_date=_parse_date(start_date), end_date=_parse_date(end_date))}


@router.get("/transactions", status_code=status.HTTP_200_OK)
def get_transactions(
    type: str | None = None,
    player_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    return {
        "items": service.get_transactions(
            type=type,
            player_id=player_id,
            limit=limit,
            offset=offset,
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
        ),
        "limit": limit,
        "offset": offset,
    }


@router.get("/pools/{pool_id}/history", status_code=status.HTTP_200_OK)
def get_pool_history(
    pool_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    return {
        "items": service.get_pool_history(
            pool_id=pool_id,
            limit=limit,
            offset=offset,
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
        ),
        "limit": limit,
        "offset": offset,
    }


@router.get("/search", status_code=status.HTTP_200_OK)
def search(q: str = Query(..., min_length=1)) -> dict:
    return {"items": service.search(query=q)}


@router.get("/export", status_code=status.HTTP_200_OK)
def export_history(
    type: str = Query(..., pattern="^(blocks|transactions|pool_history)$"),
    format: str = Query(..., pattern="^(csv|json)$"),
    player_id: str | None = None,
    pool_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> StreamingResponse:
    start_at = _parse_date(start_date)
    end_at = _parse_date(end_date)
    if type == "blocks" and format == "csv":
        return StreamingResponse(
            export_service.export_blocks_csv(start_at, end_at),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="blocks.csv"'},
        )
    if type == "transactions" and format == "json":
        return StreamingResponse(
            export_service.export_transactions_json(player_id, start_at, end_at),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="transactions.json"'},
        )
    if type == "pool_history" and format == "csv":
        if not pool_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pool_id_required")
        return StreamingResponse(
            export_service.export_pool_history_csv(pool_id),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="pool-{pool_id}.csv"'},
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_export")
