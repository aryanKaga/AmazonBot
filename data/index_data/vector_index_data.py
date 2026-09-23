import ast
import json
import os
from pathlib import Path

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


DATA_DIR = Path(__file__).resolve().parent.parent
CONVERSATIONS_PATH = DATA_DIR / "conversations.json"
CUSTOMER_DF_PATH = DATA_DIR / "customer_df.csv"
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "amazon_customer_queries")
BATCH_SIZE = 256


def load_conversations():
    with CONVERSATIONS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_embedding(value):
    if isinstance(value, str):
        value = ast.literal_eval(value)
    return [float(item) for item in value]


def index_customer_queries():
    conversations = load_conversations()
    client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        timeout=5,
    )

    customer_rows = pd.read_csv(
        CUSTOMER_DF_PATH,
        usecols=["tweet_id", "embeddings"],
        chunksize=BATCH_SIZE,
    )
    first_chunk = next(customer_rows, None)
    if first_chunk is None:
        raise ValueError("customer_df.csv does not contain any rows")

    first_embedding = parse_embedding(first_chunk.iloc[0]["embeddings"])
    if not first_embedding:
        raise ValueError("The first embedding is empty")

    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=len(first_embedding),
            distance=Distance.COSINE,
        ),
    )

    total_indexed = 0
    for chunk in (chunk for chunk in [first_chunk] if chunk is not None):
        total_indexed += upsert_chunk(client, chunk, conversations)

    for chunk in customer_rows:
        total_indexed += upsert_chunk(client, chunk, conversations)

    print(f"Indexed {total_indexed} customer queries in '{COLLECTION_NAME}'")


def upsert_chunk(client, chunk, conversations):
    points = []
    for row in chunk.itertuples(index=False):
        tweet_id = str(row.tweet_id).strip()
        if tweet_id not in conversations:
            raise ValueError(f"No conversation found for tweet_id {tweet_id}")

        vector = parse_embedding(row.embeddings)
        points.append(
            PointStruct(
                id=int(tweet_id),
                vector=vector,
                payload={
                    "tweet_id": tweet_id,
                    "query": conversations[tweet_id]["query"],
                },
            )
        )

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


if __name__ == "__main__":
    index_customer_queries()




