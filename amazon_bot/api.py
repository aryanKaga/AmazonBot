import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError
from sqlalchemy import text
from amazon_bot.schemas import ChatRequest, ChatResponse, ConversationTurn
from amazon_bot.config import get_settings
from amazon_bot.human_bucket import claim_ticket, list_tickets
from amazon_bot.tasks import process_chat
import logging
from uuid import uuid4
from amazon_bot.database import SessionLocal, engine
from amazon_bot import models

logger = logging.getLogger(__name__)

# Create tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Amazon Bot Assistant API", version="1.0.0")

def get_redis():
    return Redis.from_url(get_settings().redis_url)

def get_queue():
    return Queue(connection=get_redis())

def get_session_history(session_id: str) -> list:
    with SessionLocal() as db:
        conv = db.query(models.Conversation).filter(models.Conversation.session_id == session_id).first()
        if conv:
            return conv.history
        return []

def save_session_history(session_id: str, history: list):
    with SessionLocal() as db:
        conv = db.query(models.Conversation).filter(models.Conversation.session_id == session_id).first()
        if conv:
            conv.history = history
        else:
            conv = models.Conversation(session_id=session_id, history=history)
            db.add(conv)
        db.commit()

@app.get("/health")
def health():
    settings = get_settings()
    try:
        r = get_redis()
        r.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "error"
    
    try:
        with SessionLocal() as db:
            db_status = "ok" if db.execute(text("SELECT 1")).scalar() == 1 else "error"
    except Exception:
        db_status = "error"
    
    return {"status": "ok", "qdrant_collection": settings.qdrant_collection_name,
            "gemini_model": settings.gemini_model, "human_queue_size": len(list_tickets()),
            "redis_status": redis_status, "db_status": db_status}

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
    with SessionLocal() as db:
        conv = db.query(models.Conversation).filter(models.Conversation.session_id == session_id).first()
        if conv:
            db.delete(conv)
            db.commit()
    return {"status": "cleared", "session_id": session_id}

class TaskResponse(BaseModel):
    task_id: str
    status: str

@app.post("/chat", response_model=TaskResponse)
def chat(request: ChatRequest):
    history = get_session_history(request.session_id)
    queue = get_queue()
    job = queue.enqueue(process_chat, request.query, request.user_id, history)
    
    r = get_redis()
    r.set(f"job_meta:{job.id}", json.dumps({"session_id": request.session_id, "query": request.query}), ex=3600)
    
    return TaskResponse(task_id=job.id, status="pending")

@app.get("/chat/status/{task_id}")
def chat_status(task_id: str):
    queue = get_queue()
    r = get_redis()
    try:
        job = Job.fetch(task_id, connection=r)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="Task not found")

    if job.is_failed:
        raise HTTPException(status_code=502, detail="Task failed during execution")

    if not job.is_finished:
        return {"status": "pending"}

    result = job.result
    if result["status"] == "error":
        raise HTTPException(status_code=502, detail=f"workflow failed: {result['error']}", headers={"X-Request-ID": result['request_id']})
    
    state = result["state"]
    
    meta_data = r.get(f"job_meta:{task_id}")
    if meta_data:
        meta = json.loads(meta_data)
        session_id = meta["session_id"]
        query = meta["query"]
        history = get_session_history(session_id)
        
        response = state["final_response"]
        answer = response.get("answer")
        new_turns = [{"role": "user", "text": query}]
        if answer:
            new_turns.append({"role": "assistant", "text": answer})
        
        history.extend(new_turns)
        save_session_history(session_id, history)
        
        human_bucket_payload = None
        if response["status"] == "escalated":
            human_bucket_payload = {
                "query": query,
                "user_id": state.get("user_id"),
                "intent": state.get("intent", "unknown"),
                "confidence": state.get("confidence", 0),
                "retrieved_conversations": state.get("reranked_conversations", []),
                "answer": state.get("answer"),
                "review_result": state.get("review_result"),
                "escalation_reason": state.get("escalation_reason"),
                "ticket": state.get("human_ticket"),
            }
            
        r.delete(f"job_meta:{task_id}")
        
        final_chat_response = {
            "status": response["status"], "answer": answer, "session_id": session_id,
            "conversation": history,
            "intent": state.get("intent", "unknown"), "confidence": state.get("confidence", 0),
            "retrieved_conversations": state.get("reranked_conversations", []),
            "review_result": state.get("review_result"),
            "escalation_reason": state.get("escalation_reason"),
            "human_bucket": human_bucket_payload,
        }
        r.set(f"job_result:{task_id}", json.dumps(final_chat_response), ex=3600)
        return final_chat_response
    else:
        cached_result = r.get(f"job_result:{task_id}")
        if cached_result:
            return json.loads(cached_result)
        return {"status": "completed_but_lost_result"}
