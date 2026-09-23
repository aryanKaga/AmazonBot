import json
import logging
import os
import re
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

from data.index_data.qdrant import retrieve_similar_queries_by_text

logger = logging.getLogger(__name__)
human_queue: Dict[str, Dict[str, Any]] = {}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONVERSATIONS_PATH = DATA_DIR / "conversations.json"
MAX_CONTEXT = 5
DEFAULT_INTENTS = [
    "Delivery / Shipping Issue",
    "Customer Service Complaint / Escalation",
    "Device & App Technical Support",
    "Damaged / Wrong / Defective Item",
    "Order Cancellation / Refund",
    "Payment, Billing & Gift Card Issues",
    "Account Access & Security",
    "Pre-order Issues",
    "Prime Membership & Billing",
    "Resolved / Successful Query",
    "Other / Needs Clarification",
]


def _load_conversations() -> Dict[str, Any]:
    with CONVERSATIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _tokens(value: str) -> set:
    return set(re.findall(r"[a-z0-9']+", value.lower()))


def rerank_results(query: str, results: List[Dict[str, Any]], limit: int = MAX_CONTEXT) -> List[Dict[str, Any]]:
    """Blend Qdrant similarity with lexical overlap to make retrieval explainable."""
    query_tokens = _tokens(query)
    ranked = []
    for result in results:
        text_tokens = _tokens(result.get("query", ""))
        overlap = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
        vector_score = float(result.get("score") or 0.0)
        result = dict(result)
        result["rerank_score"] = (0.7 * vector_score) + (0.3 * overlap)
        ranked.append(result)
    return sorted(ranked, key=lambda item: item["rerank_score"], reverse=True)[:limit]


def _conversation_context(results: List[Dict[str, Any]], conversations: Dict[str, Any]) -> List[Dict[str, Any]]:
    context = []
    for result in results:
        item = conversations.get(str(result.get("tweet_id")), {})
        context.append(
            {
                "query": result.get("query", ""),
                "similarity": round(float(result.get("rerank_score", result.get("score", 0.0))), 4),
                "conversation": item.get("conversation", {}).get("messages", []),
            }
        )
    return context


def _gemini_generate(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed ({error.code}): {detail[:300]}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Gemini request could not reach the service: {error.reason}") from error

    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("Gemini returned no usable text") from error


def _classify_and_answer(query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
    prompt = f"""
You are an Amazon support routing and response assistant.
Classify the customer query into exactly one intent from this list:
{json.dumps(DEFAULT_INTENTS)}

Use the retrieved historical conversations only as guidance. Do not claim to access a
real order, account, payment, or customer database. If an example order/customer is
needed to explain a workflow, mark it explicitly as hypothetical. Escalate when the
customer requests a human, reports fraud/security risk, has a safety issue, is
repeatedly dissatisfied, or the retrieved context is not relevant.

Return JSON only with this shape:
{{"intent": "...", "confidence": 0.0, "escalate": false,
  "answer": "...", "missing_information": ["..."]}}

Customer query:
{query}

Retrieved conversations:
{json.dumps(context, ensure_ascii=False)}
"""
    raw = _gemini_generate(prompt)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError("Gemini returned invalid routing JSON") from error

    intent = result.get("intent")
    if intent not in DEFAULT_INTENTS:
        result["intent"] = "Other / Needs Clarification"
    result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
    result["escalate"] = bool(result.get("escalate", False))
    result["missing_information"] = result.get("missing_information", [])
    result["answer"] = str(result.get("answer", "")).strip()
    if not result["answer"]:
        raise RuntimeError("Gemini returned an empty answer")
    if result["confidence"] < float(os.getenv("ESCALATION_CONFIDENCE", "0.45")):
        result["escalate"] = True
    return result


def handle_query(query: str, user_id: str = "anonymous") -> Dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    query = query.strip()
    try:
        retrieved = retrieve_similar_queries_by_text(query, limit=10)
    except Exception as error:
        logger.exception("Qdrant retrieval failed")
        raise RuntimeError("Unable to retrieve support context") from error

    conversations = _load_conversations()
    reranked = rerank_results(query, retrieved)
    result = _classify_and_answer(query, _conversation_context(reranked, conversations))
    response = {
        "user_id": user_id,
        "intent": result["intent"],
        "confidence": result["confidence"],
        "answer": result["answer"],
        "missing_information": result["missing_information"],
        "escalated": result["escalate"],
        "retrieved_conversations": [
            {
                "tweet_id": item.get("tweet_id"),
                "score": item.get("rerank_score"),
                "query": item.get("query"),
            }
            for item in reranked
        ],
    }
    if result["escalate"]:
        ticket_id = str(uuid.uuid4())
        response["human_bucket"] = {
            "ticket_id": ticket_id,
            "status": "queued",
            "reason": "low confidence or policy-required human review",
            "user_id": user_id,
        }
        human_queue[ticket_id] = {
            **response["human_bucket"],
            "query": query,
            "answer": result["answer"],
            "intent": result["intent"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return response


def list_human_tickets() -> List[Dict[str, Any]]:
    return list(human_queue.values())


def claim_human_ticket(ticket_id: str) -> Dict[str, Any]:
    ticket = human_queue.get(ticket_id)
    if ticket is None:
        raise KeyError(ticket_id)
    ticket["status"] = "claimed"
    ticket["claimed_at"] = datetime.now(timezone.utc).isoformat()
    return ticket
