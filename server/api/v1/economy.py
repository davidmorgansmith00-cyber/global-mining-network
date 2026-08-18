from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import APIRouter, HTTPException, Request, status

from domain.economy.analyzer import EconomyAnalyzer
from domain.economy.experiment import get_economy_experiment_service
from domain.economy.parameters import get_economy_parameter_service
from shared.settings import settings


router = APIRouter(tags=["economy"])

_analyzer = EconomyAnalyzer()
_parameter_service = get_economy_parameter_service()
_experiment_service = get_economy_experiment_service()
_analysis_cache: dict[str, object] = {"expires_at": datetime.min.replace(tzinfo=UTC), "value": None}
_analysis_cache_lock = Lock()


def _is_authorized(request: Request) -> bool:
    current_token = settings.maintenance_auth_token
    previous_token = settings.maintenance_auth_previous_token
    provided = request.headers.get(settings.maintenance_auth_header)
    if current_token and provided == current_token:
        return True
    if previous_token and provided == previous_token:
        return True
    return False


def _require_admin(request: Request) -> None:
    if not _is_authorized(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


@router.get("/economy/parameters", status_code=status.HTTP_200_OK)
def get_economy_parameters() -> dict:
    return _parameter_service.get_current_parameters().to_public_dict()


@router.get("/economy/analysis", status_code=status.HTTP_200_OK)
def get_economy_analysis() -> dict:
    with _analysis_cache_lock:
        now = datetime.now(UTC)
        expires_at = _analysis_cache["expires_at"]
        if isinstance(expires_at, datetime) and now < expires_at and _analysis_cache["value"] is not None:
            return _analysis_cache["value"]  # type: ignore[return-value]

        spending = _analyzer.analyze_spending_patterns()
        inflation = _analyzer.calculate_inflation_rate(days=1)
        churn = _analyzer.calculate_churn_rate(days=7)
        progression = _analyzer.analyze_progression_distribution()

        value = {
            "generated_at": now.isoformat(),
            "avg_player_balance": spending.get("avg_spend_per_player", "0"),
            "inflation_rate_percent": inflation["inflation_rate_percent"],
            "churn_rate_percent": churn["churn_rate_percent"],
            "median_tier": progression["median_tier"],
            "recommendations": _analyzer.recommend_parameter_tuning(),
            "cache_ttl_seconds": int(timedelta(hours=1).total_seconds()),
        }
        _analysis_cache["value"] = value
        _analysis_cache["expires_at"] = now + timedelta(hours=1)
        return value


@router.get("/economy/experiments/active", status_code=status.HTTP_200_OK)
def get_active_experiments() -> dict:
    return {"experiments": _experiment_service.list_active_experiments()}


@router.get("/admin/economy/parameters/history", status_code=status.HTTP_200_OK)
def get_economy_parameter_history(request: Request) -> dict:
    _require_admin(request)
    history = _parameter_service.get_history()
    return {
        "history": [
            {
                "parameter_version": item.parameter_version,
                "previous_version": item.previous_version,
                "change_log": item.change_log,
                "reverted_at": item.reverted_at.isoformat() if item.reverted_at else None,
                "reverted_by_admin_id": item.reverted_by_admin_id,
            }
            for item in history
        ]
    }


@router.get("/admin/economy/experiment/{experiment_id}/results", status_code=status.HTTP_200_OK)
def get_experiment_results(experiment_id: str, request: Request) -> dict:
    _require_admin(request)
    try:
        return _experiment_service.analyze_experiment_results(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
