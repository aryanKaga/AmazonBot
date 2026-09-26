import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4
from amazon_bot.models import HumanTicket
from amazon_bot.database import SessionLocal

def _json_safe(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value

def create_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    ticket_id = f"HB-{uuid4().hex[:10].upper()}"
    with SessionLocal() as db:
        ticket = HumanTicket(
            ticket_id=ticket_id,
            status="queued",
            payload=_json_safe(payload),
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            **ticket.payload
        }

def list_tickets() -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        tickets = db.query(HumanTicket).all()
        return [
            {
                "ticket_id": t.ticket_id,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "claimed_at": t.claimed_at.isoformat() if t.claimed_at else None,
                **t.payload
            }
            for t in tickets
        ]

def claim_ticket(ticket_id: str) -> Dict[str, Any] | None:
    with SessionLocal() as db:
        ticket = db.query(HumanTicket).filter(HumanTicket.ticket_id == ticket_id).first()
        if not ticket:
            return None
        ticket.status = "claimed"
        ticket.claimed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ticket)
        return {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "claimed_at": ticket.claimed_at.isoformat() if ticket.claimed_at else None,
            **ticket.payload
        }
