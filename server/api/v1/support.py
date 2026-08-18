from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from domain.support.service import SupportService


router = APIRouter(tags=["support"])
_service = SupportService()


class ReportRequest(BaseModel):
    player_id: str
    title: str
    description: str
    category: str | None = None
    screenshot_b64: str | None = None
    logs_b64: str | None = None
    player_state: dict | None = None
    environment_info: dict | None = None


class MessageRequest(BaseModel):
    from_role: str
    message_text: str


class StatusUpdateRequest(BaseModel):
    status: str
    staff_id: str


class CloseRequest(BaseModel):
    resolution_reason: str
    staff_id: str


@router.post("/support/report", status_code=status.HTTP_201_CREATED)
def create_report(req: ReportRequest) -> dict:
    ticket_id = _service.create_ticket(
        player_id=req.player_id,
        title=req.title,
        description=req.description,
        category=req.category,
        screenshot_b64=req.screenshot_b64,
        logs_b64=req.logs_b64,
        player_state=req.player_state,
        environment_info=req.environment_info,
    )
    return {"ticket_id": ticket_id}


@router.get("/support/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    ticket = _service.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    messages = _service.get_ticket_messages(ticket_id)
    return {
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "player_id": ticket.player_id,
            "category": ticket.category,
            "title": ticket.title,
            "description": ticket.description,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat(),
            "first_response_at": ticket.first_response_at.isoformat() if ticket.first_response_at else None,
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
            "resolution_reason": ticket.resolution_reason,
        },
        "messages": [
            {
                "message_id": m.message_id,
                "from_role": m.from_role,
                "message_text": m.message_text,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/support/tickets/{ticket_id}/message", status_code=status.HTTP_201_CREATED)
def add_message(ticket_id: str, req: MessageRequest) -> dict:
    message_id = _service.add_message(ticket_id, req.from_role, req.message_text)
    return {"message_id": message_id}


@router.get("/support/tickets")
def search_tickets(
    player_id: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    tickets = _service.search_tickets(
        player_id=player_id,
        category=category,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "tickets": [
            {
                "ticket_id": t.ticket_id,
                "player_id": t.player_id,
                "category": t.category,
                "title": t.title,
                "priority": t.priority,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in tickets
        ]
    }


@router.post("/support/tickets/{ticket_id}/status")
def update_status(ticket_id: str, req: StatusUpdateRequest) -> dict:
    try:
        new_status = _service.update_ticket_status(ticket_id, req.status, req.staff_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": new_status}


@router.post("/support/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str, req: CloseRequest) -> dict:
    _service.close_ticket(ticket_id, req.resolution_reason, req.staff_id)
    return {"closed": True}


@router.get("/support/sla-metrics")
def sla_metrics() -> dict:
    metrics = _service.get_ticket_sla_metrics()
    return {
        "avg_first_response_seconds": metrics.avg_first_response_seconds,
        "avg_resolution_seconds": metrics.avg_resolution_seconds,
        "total_tickets": metrics.total_tickets,
        "open_tickets": metrics.open_tickets,
    }
