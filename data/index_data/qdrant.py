import os

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse


COLLECTION_NAME = "amazon_customer_queries"
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
_embedding_model = None


def get_qdrant_client():
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        timeout=5,
    )


def encode_query(query):
    """Encode a text query using the model used by the Qdrant vectors."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise ImportError(
                "Install the query encoder with: "
                "pip install sentence-transformers"
            ) from error
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _embedding_model.encode(query, convert_to_numpy=False).tolist()


def retrieve_similar_queries_by_text(query, limit=5, score_threshold=None):
    """Encode a text query and return its most similar stored queries."""
    return retrieve_similar_queries(
        encode_query(query),
        limit=limit,
        score_threshold=score_threshold,
    )


def retrieve_similar_queries(query_embedding, limit=5, score_threshold=None):
    """Return queries most similar to the supplied embedding."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    client = get_qdrant_client()
    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=[float(value) for value in query_embedding],
        limit=limit,
        score_threshold=score_threshold,
        with_payload=True,
    )

    return [
        {
            "score": point.score,
            "tweet_id": point.payload.get("tweet_id"),
            "query": point.payload.get("query"),
        }
        for point in response.points
    ]


def test_qdrant_connection():
    # Connect to local Docker instance on default REST port 6333
    client = get_qdrant_client()

    try:
        # Check server health / collections list to verify connectivity
        collections = client.get_collections()
        print(" Successfully connected to Qdrant!")
        print(f"Existing Collections Count: {len(collections.collections)}")
        
    except UnexpectedResponse as e:
        print(f" Failed to connect. Qdrant returned an error: {e}")
    except Exception as e:
        print(f" Could not reach Qdrant server. Ensure Docker container is running.")
        print(f"Error details: {e}")


def example_text_query_retrieval():
    query = "My package delivery is delayed and has not arrived."
    results = retrieve_similar_queries_by_text(query, limit=3)

    print(f"\nQuery: {query}")
    for result in results:
        print(
            f"score={result['score']:.4f} "
            f"tweet_id={result['tweet_id']} "
            f"query={result['query']}"
        )


if __name__ == "__main__":
    test_qdrant_connection()
    example_text_query_retrieval()