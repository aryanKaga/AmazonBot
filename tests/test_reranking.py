from amazon_bot.reranking import rerank
from amazon_bot.schemas import Classification, Conversation


def test_rerank_returns_at_most_five_and_prefers_resolved_overlap():
    classification = Classification(
        is_relevant=True, intent="delivery_issue", confidence=0.93, reason="delivery"
    )
    candidates = [
        Conversation(
            conversation_id=str(index),
            query="my delivery package is late" if index == 0 else "unrelated account issue",
            messages=[{"inbound": False, "text": "resolution"}] if index == 0 else [],
            semantic_score=0.9 if index == 0 else 0.8,
        )
        for index in range(10)
    ]
    result = rerank("package delivery is late", classification, candidates)
    assert len(result) == 5
    assert result[0].conversation_id == "0"
