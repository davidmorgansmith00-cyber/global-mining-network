"""GMN-EC-08: Admin analytics/funnel endpoints.

All endpoints require the maintenance auth token (operator role).

Endpoints:
  GET /admin/analytics/funnel?cohort_date=YYYY-MM-DD  → cohort conversion rates
  GET /admin/analytics/time-to-tier?tier=2            → median time to reach tier
  GET /admin/analytics/retention?tier=1               → retention funnel
  GET /admin/analytics/churn-risk                     → at-risk players
  GET /admin/analytics/purchase-frequency             → avg purchases per player
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from domain.telemetry.service import (
    query_churn_risk_players,
    query_funnel_cohort_conversion,
    query_funnel_time_to_tier,
    query_progression_funnel,
    query_purchase_frequency,
    query_retention_funnel,
)
from shared.settings import settings


router = APIRouter(prefix="/admin/analytics", tags=["analytics"])


def _is_authorized(request: Request) -> bool:
    """Return True if the request carries a valid maintenance auth token.

    Denies access when no tokens are configured (secure by default).
    """
    current_token = settings.maintenance_auth_token
    previous_token = settings.maintenance_auth_previous_token
    provided_token = request.headers.get(settings.maintenance_auth_header)

    if current_token and provided_token == current_token:
        return True
    if previous_token and provided_token == previous_token:
        return True
    return False


def _require_auth(request: Request) -> None:
    if not _is_authorized(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


@router.get("/funnel", status_code=status.HTTP_200_OK)
def get_funnel_conversion(
    request: Request,
    cohort_date: str = Query(..., description="Cohort date in YYYY-MM-DD format"),
) -> dict:
    """Return Tier 1→2→3 conversion rates for players created on cohort_date."""
    _require_auth(request)
    result = query_funnel_cohort_conversion(cohort_date)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"])
    return result


@router.get("/progression-funnel", status_code=status.HTTP_200_OK)
def get_progression_funnel(
    request: Request,
    cohort_date: str | None = Query(None, description="Optional cohort date in YYYY-MM-DD format"),
) -> dict:
    """Return progression funnel counts, drop-off rates, and median inter-stage durations."""
    _require_auth(request)
    result = query_progression_funnel(cohort_date=cohort_date)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"])
    return result


@router.get("/time-to-tier", status_code=status.HTTP_200_OK)
def get_time_to_tier(
    request: Request,
    tier: int = Query(..., ge=2, description="Target tier (2 or 3)"),
) -> dict:
    """Return median elapsed seconds from player creation to reaching the given tier."""
    _require_auth(request)
    result = query_funnel_time_to_tier(tier)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"])
    return result


@router.get("/retention", status_code=status.HTTP_200_OK)
def get_retention_funnel(
    request: Request,
    tier: int | None = Query(None, description="Filter by player tier (omit for all tiers)"),
) -> list:
    """Return player counts grouped by tier and last-activity recency bucket."""
    _require_auth(request)
    result = query_retention_funnel(tier)
    if result and "error" in result[0]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result[0]["error"])
    return result


@router.get("/churn-risk", status_code=status.HTTP_200_OK)
def get_churn_risk(request: Request) -> list:
    """Return tier 1/2 players inactive for 7+ days."""
    _require_auth(request)
    result = query_churn_risk_players()
    if result and "error" in result[0]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result[0]["error"])
    return result


@router.get("/purchase-frequency", status_code=status.HTTP_200_OK)
def get_purchase_frequency(request: Request) -> dict:
    """Return average hardware purchases per player by cohort month."""
    _require_auth(request)
    result = query_purchase_frequency()
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"])
    return result
