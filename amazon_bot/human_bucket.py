from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List
from uuid import uuid4

_tickets: Dict[str, Dict[str, Any]] = {}
_lock = Lock()


def _json_safe(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def create_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    ticket = {
        "ticket_id": f"HB-{uuid4().hex[:10].upper()}",
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **_json_safe(payload),
    }
    with _lock:
        _tickets[ticket["ticket_id"]] = ticket
    return ticket


def list_tickets() -> List[Dict[str, Any]]:
    with _lock:
        return list(_tickets.values())


def claim_ticket(ticket_id: str) -> Dict[str, Any] | None:
    with _lock:
        ticket = _tickets.get(ticket_id)
        if ticket is None:
            return None
        ticket["status"] = "claimed"
        ticket["claimed_at"] = datetime.now(timezone.utc).isoformat()
        return ticket
