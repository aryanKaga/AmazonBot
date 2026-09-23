from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Classification(BaseModel):
    is_relevant: bool
    intent: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class Conversation(BaseModel):
    conversation_id: str
    query: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    semantic_score: float = 0
    rerank_score: float = 0
    usefulness_score: float = 0


class ReviewResult(BaseModel):
    approved: bool
    score: float = Field(ge=0, le=1)
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    requires_human: bool = False


class UserContext(BaseModel):
    user_id: str
    synthetic: bool = True
    profile: Dict[str, Any] = Field(default_factory=dict)
    orders: List[Dict[str, Any]] = Field(default_factory=list)
    subscriptions: List[Dict[str, Any]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    user_id: str = "demo_user_001"
    session_id: str = "demo-session"


class ConversationTurn(BaseModel):
    role: str
    text: str


class ChatResponse(BaseModel):
    status: str
    session_id: str = "demo-session"
    conversation: List[ConversationTurn] = Field(default_factory=list)
    answer: Optional[str] = None
    intent: str
    confidence: float
    retrieved_conversations: List[Conversation] = Field(default_factory=list)
    review_result: Optional[ReviewResult] = None
    escalation_reason: Optional[str] = None
    human_bucket: Optional[Dict[str, Any]] = None
