from __future__ import annotations

from fastapi import APIRouter

from domain.monitoring.service import get_alerter, get_error_tracker, get_metrics_collector


router = APIRouter(tags=["monitoring"])


@router.get("/monitoring/errors")
def list_errors() -> dict:
    records = get_error_tracker().get_all()
    return {
        "errors": [
            {
                "fingerprint": r.fingerprint,
                "message": r.message,
                "count": r.count,
                "affected_users": len(r.affected_users),
                "first_seen": r.first_seen.isoformat(),
                "last_seen": r.last_seen.isoformat(),
            }
            for r in records
        ]
    }


@router.get("/monitoring/metrics")
def get_metrics() -> dict:
    return get_metrics_collector().summary()


@router.get("/monitoring/alerts")
def get_alerts() -> dict:
    alerter = get_alerter()
    alerter.evaluate()
    alerts = alerter.get_active_alerts()
    return {
        "alerts": [
            {
                "rule_name": a.rule_name,
                "severity": a.severity,
                "message": a.message,
                "triggered_at": a.triggered_at.isoformat(),
            }
            for a in alerts
        ]
    }


@router.get("/health")
def health_check() -> dict:
    from shared.database import database_is_configured

    db_ok = False
    if database_is_configured():
        try:
            from shared.database import open_connection

            with open_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            db_ok = True
        except Exception:
            pass
    else:
        db_ok = None  # type: ignore[assignment]

    overall = "green" if db_ok is not False else "yellow"
    return {
        "status": overall,
        "database": "ok" if db_ok else ("not_configured" if db_ok is None else "error"),
    }


@router.get("/health/ready")
def readiness_check() -> dict:
    from shared.database import database_is_configured

    checks: dict[str, str] = {}
    all_ok = True

    if database_is_configured():
        try:
            from shared.database import open_connection

            with open_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
            all_ok = False
    else:
        checks["database"] = "not_configured"

    return {
        "ready": all_ok,
        "status": "green" if all_ok else "red",
        "checks": checks,
    }
