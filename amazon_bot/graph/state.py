from typing import Any, Dict, List, Optional, TypedDict
from amazon_bot.schemas import Classification, Conversation, ConversationTurn, ReviewResult, UserContext


class GraphState(TypedDict, total=False):
    query: str
    user_id: str
    history: List[ConversationTurn]
    intent: str
    confidence: float
    is_relevant: bool
    classification_reason: str
    retrieved_candidates: List[Conversation]
    reranked_conversations: List[Conversation]
    user_context: UserContext
    answer: str
    review_result: ReviewResult
    iteration_count: int
    requires_human: bool
    escalation_reason: str
    human_ticket: Dict[str, Any]
    final_response: Dict[str, Any]
