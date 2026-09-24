from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from amazon_bot.graph.workflow import workflow
from amazon_bot.schemas import ChatRequest, ChatResponse
from amazon_bot.config import get_settings
from amazon_bot.human_bucket import claim_ticket, list_tickets
from amazon_bot.schemas import ConversationTurn
from threading import Lock
import logging
from uuid import uuid4

_sessions = {}
_sessions_lock = Lock()
logger = logging.getLogger(__name__)

app = FastAPI(title="Amazon Bot Assistant", version="1.0.0")
FRONTEND_PATH = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_PATH)


@app.get("/health")
def health():
    settings = get_settings()
    return {"status": "ok", "qdrant_collection": settings.qdrant_collection_name,
            "gemini_model": settings.gemini_model, "human_queue_size": len(list_tickets())}


@app.get("/human-bucket")
def human_bucket():
    return {"tickets": list_tickets()}


@app.post("/human-bucket/{ticket_id}/claim")
def claim_human_ticket(ticket_id: str):
    ticket = claim_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="human ticket not found")
    return ticket


@app.delete("/sessions/{session_id}")
def clear_session(session_id: str):
    with _sessions_lock:
        _sessions.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    with _sessions_lock:
        history = list(_sessions.get(request.session_id, []))
    try:
        state = workflow.invoke({
            "query": request.query,
            "user_id": request.user_id,
            "history": [ConversationTurn(**turn) for turn in history],
        })
    except Exception as error:
        request_id = uuid4().hex[:12]
        logger.exception("Workflow failed request_id=%s session_id=%s", request_id, request.session_id)
        raise HTTPException(
            status_code=502,
            detail=f"workflow failed: {error}",
            headers={"X-Request-ID": request_id},
        ) from error
    response = state["final_response"]
    answer = response.get("answer")
    new_turns = [{"role": "user", "text": request.query}]
    if answer:
        new_turns.append({"role": "assistant", "text": answer})
    with _sessions_lock:
        _sessions[request.session_id] = history + new_turns
    human_bucket = None
    if response["status"] == "escalated":
        human_bucket = {
            "query": request.query,
            "user_id": request.user_id,
            "intent": state.get("intent", "unknown"),
            "confidence": state.get("confidence", 0),
            "retrieved_conversations": state.get("reranked_conversations", []),
            "answer": state.get("answer"),
            "review_result": state.get("review_result"),
            "escalation_reason": state.get("escalation_reason"),
            "ticket": state.get("human_ticket"),
        }
    return ChatResponse(
        status=response["status"], answer=answer, session_id=request.session_id,
        conversation=[ConversationTurn(**turn) for turn in _sessions[request.session_id]],
        intent=state.get("intent", "unknown"), confidence=state.get("confidence", 0),
        retrieved_conversations=state.get("reranked_conversations", []),
        review_result=state.get("review_result"),
        escalation_reason=state.get("escalation_reason"),
        human_bucket=human_bucket,
    )
