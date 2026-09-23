import json
from amazon_bot.intents import INTENTS


def _conversation_dicts(conversations):
    return [
        item.model_dump() if hasattr(item, "model_dump") else item
        for item in conversations
    ]


def _history_text(history):
    if not history:
        return "(no earlier messages)"
    return "\n".join(f"{item.role}: {item.text}" for item in history)


def classification_prompt(query: str, history=None) -> str:
    return f"""Classify this Amazon support query.
Return only the structured schema. An irrelevant query is unrelated to Amazon
support. Choose one intent from {json.dumps(INTENTS)}.
The latest message may be a follow-up to the earlier conversation. Use the
conversation history when resolving references such as "yes", "that email",
"the order", or "I already tried it".
Conversation history:
{_history_text(history or [])}
Query: {query}"""


def answer_prompt(query, intent, conversations, user_context, history=None) -> str:
    return f"""You are an Amazon support assistant. Answer using only the query,
intent, historical conversations, and synthetic context below. Never invent
order status, refunds, policy, account data, or completed actions. If evidence
is insufficient, say that a human needs to review it. Synthetic context is
hypothetical and must never be presented as real.
Query: {query}
Intent: {intent}
Conversation history:
{_history_text(history or [])}
Historical conversations: {json.dumps(_conversation_dicts(conversations), ensure_ascii=False)}
User context: {user_context.model_dump_json()}"""


def review_prompt(query, intent, conversations, answer, history=None) -> str:
    return f"""Review this Amazon support answer independently. Reject unsupported
claims, hallucinated status/policies/actions, irrelevant responses, missing
evidence, or requests that require a human.
Query: {query}
Intent: {intent}
Conversation history:
{_history_text(history or [])}
Evidence: {json.dumps(_conversation_dicts(conversations), ensure_ascii=False)}
Answer: {answer}"""
