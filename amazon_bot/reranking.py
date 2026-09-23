import re
from typing import List
from amazon_bot.schemas import Classification, Conversation


def _words(text: str):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def rerank(query: str, classification: Classification, candidates: List[Conversation]) -> List[Conversation]:
    query_words = _words(query)
    ranked = []
    for conversation in candidates:
        problem_words = _words(conversation.query)
        intent_words = _words(classification.intent.replace("_", " "))
        overlap = len(query_words & problem_words) / max(len(query_words), 1)
        intent_overlap = len(_words(conversation.query) & intent_words) / max(len(intent_words), 1)
        has_resolution = any(not message.get("inbound", True) for message in conversation.messages)
        usefulness = 1.0 if has_resolution else 0.3
        conversation.usefulness_score = usefulness
        conversation.rerank_score = (
            0.55 * conversation.semantic_score
            + 0.25 * overlap
            + 0.10 * intent_overlap
            + 0.10 * usefulness
        )
        ranked.append(conversation)
    return sorted(ranked, key=lambda item: item.rerank_score, reverse=True)[:5]
