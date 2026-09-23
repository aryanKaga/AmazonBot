from amazon_bot.config import get_settings
from amazon_bot.llm.client import structured_llm, get_llm
from amazon_bot.llm.prompts import classification_prompt, answer_prompt, review_prompt
from amazon_bot.retrieval import retrieve_candidates
from amazon_bot.reranking import rerank
from amazon_bot.schemas import Classification, ReviewResult
from amazon_bot.synthetic_users import SyntheticUserRepository
from amazon_bot.human_bucket import create_ticket

_HUMAN_TRIGGER_TERMS = (
    "human", "agent", "representative", "fraud", "hacked", "stolen",
    "unauthorized", "unsafe", "danger", "lawsuit", "legal complaint",
)


def _content_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        ).strip()
    return str(content)


def classify_query(state):
    query_lower = state["query"].lower()
    result = structured_llm(Classification).invoke(
        classification_prompt(state["query"], state.get("history", []))
    )
    values = result.model_dump()
    if any(term in query_lower for term in _HUMAN_TRIGGER_TERMS):
        values["is_relevant"] = True
        values["confidence"] = 1.0
        values["reason"] = "The query contains a request or risk requiring human review."
    return {
        "is_relevant": values["is_relevant"],
        "intent": values["intent"],
        "confidence": values["confidence"],
        "classification_reason": values["reason"],
        "iteration_count": 0,
    }


def retrieve(state):
    return {"retrieved_candidates": retrieve_candidates(state["query"])}


def rerank_node(state):
    classification = Classification(
        is_relevant=state["is_relevant"], intent=state["intent"],
        confidence=state["confidence"], reason=state["classification_reason"],
    )
    return {"reranked_conversations": rerank(state["query"], classification, state["retrieved_candidates"])}


def load_user_context(state):
    return {"user_context": SyntheticUserRepository().get_context(state["user_id"])}


def generate_answer(state):
    prompt = answer_prompt(
        state["query"], state["intent"], state["reranked_conversations"],
        state["user_context"], state.get("history", []),
    )
    return {"answer": _content_text(get_llm().invoke(prompt))}


def review_answer(state):
    result = structured_llm(ReviewResult).invoke(review_prompt(
        state["query"], state["intent"], state["reranked_conversations"], state["answer"],
        state.get("history", []),
    ))
    return {"review_result": result, "iteration_count": state.get("iteration_count", 0) + 1}


def refine_answer(state):
    prompt = answer_prompt(
        state["query"], state["intent"], state["reranked_conversations"],
        state["user_context"], state.get("history", []),
    )
    prompt += f"\nFix these reviewer issues without adding unsupported facts: {state['review_result'].model_dump_json()}"
    return {"answer": _content_text(get_llm().invoke(prompt))}


def finalize(state):
    review = state.get("review_result")
    human = state.get("requires_human", False)
    reason = state.get("escalation_reason")
    if not state.get("is_relevant") or state.get("confidence", 0) < get_settings().escalation_confidence:
        human, reason = True, "irrelevant or low-confidence classification"
    if review and review.requires_human:
        human, reason = True, "reviewer requires human intervention"
    if review and not review.approved and state.get("iteration_count", 0) >= get_settings().max_review_iterations:
        human, reason = True, "answer was not approved after maximum review iterations"
    if human:
        reason = reason or "human review required"
        ticket = create_ticket({
            "query": state["query"],
            "user_id": state.get("user_id", "unknown"),
            "intent": state.get("intent", "unknown"),
            "confidence": state.get("confidence", 0),
            "retrieved_conversations": state.get("reranked_conversations", []),
            "answer": state.get("answer"),
            "review_result": review,
            "escalation_reason": reason,
        })
        return {
            "requires_human": True,
            "escalation_reason": reason,
            "human_ticket": ticket,
            "final_response": {"status": "escalated", "answer": state.get("answer")},
        }
    return {"final_response": {"status": "completed", "answer": state["answer"]}}
