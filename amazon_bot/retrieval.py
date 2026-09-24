import json
from pathlib import Path
from typing import List
from qdrant_client import QdrantClient
from amazon_bot.config import get_settings
from amazon_bot.schemas import Conversation
from data.index_data.qdrant import encode_query

_conversations = None


def _load_conversations():
    global _conversations
    if _conversations is None:
        path = Path(__file__).resolve().parents[1] / "data" / "conversations.json"
        with path.open(encoding="utf-8") as file:
            _conversations = json.load(file)
    return _conversations


def get_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, timeout=5)


def retrieve_candidates(query: str) -> List[Conversation]:
    settings = get_settings()
    points = get_client().query_points(
        collection_name=settings.qdrant_collection_name,
        query=encode_query(query),
        limit=settings.qdrant_candidate_limit,
        with_payload=True,
    ).points
    print('loading conversation')
    conversations = _load_conversations()
    print('covo')
    output = []
    for point in points:
        tweet_id = str(point.payload.get("tweet_id"))
        source = conversations.get(tweet_id, {})
        output.append(Conversation(
            conversation_id=str(source.get("conversation", {}).get("conversation_id", tweet_id)),
            query=source.get("query", point.payload.get("query", "")),
            messages=source.get("conversation", {}).get("messages", []),
            semantic_score=float(point.score or 0),
        ))
    return output
