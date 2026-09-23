import pandas as pd
import json
import re

dataset_df = pd.read_csv("./twcs/twcs.csv")
customer_df = pd.read_csv("./customer_df.csv")

# Normalize columns
for df in [dataset_df, customer_df]:
    for col in ["tweet_id", "author_id", "in_response_to_tweet_id", "response_tweet_id"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["text"] = df["text"].fillna("").astype(str)

def convert_inbound(x):
    return str(x).strip().lower() in {"true", "1", "yes"}

dataset_df["inbound"] = dataset_df["inbound"].apply(convert_inbound)
customer_df["inbound"] = customer_df["inbound"].apply(convert_inbound)



def normalize_id(x):
    if pd.isna(x) or x == "":
        return ""
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

for df in [dataset_df, customer_df]:
    for col in ["tweet_id", "author_id", "in_response_to_tweet_id", "response_tweet_id"]:
        df[col] = df[col].apply(normalize_id)
    df["text"] = df["text"].fillna("").astype(str)


    
def clean_text(text):
    text = re.sub(r'@[A-Za-z0-9_]+', '', text)

    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U00002600-\U000026FF"
        "\U00002B00-\U00002BFF"
        "]+",
        flags=re.UNICODE
    )

    text = emoji_pattern.sub('', text)
    return re.sub(r'\s+', ' ', text).strip()

# tweet_id -> tweet data
tweet_lookup = dataset_df.set_index("tweet_id").to_dict("index")

# parent tweet -> reply tweets
children_lookup = {}

for _, row in dataset_df.iterrows():
    parent = row["in_response_to_tweet_id"]
    if parent:
        children_lookup.setdefault(parent, []).append(row["tweet_id"])



def create_message(tweet_id):
    tweet = tweet_lookup[tweet_id]

    return {
        "tweet_id": tweet_id,
        "author_id": tweet["author_id"],
        "inbound": tweet["inbound"],
        "text": clean_text(tweet["text"]),
        "parent_tweet_id": tweet["in_response_to_tweet_id"] or None
    }

def build_conversation(root_id):
    messages = []
    participants = set()
    visited = set()

    def traverse(tweet_id):
        if tweet_id in visited or tweet_id not in tweet_lookup:
            return

        visited.add(tweet_id)
        tweet = tweet_lookup[tweet_id]

        participants.add(tweet["author_id"])
        messages.append(create_message(tweet_id))
        
        for child in children_lookup.get(tweet_id, []):
            traverse(child)

    traverse(root_id)

    return {
        "conversation_id": root_id,
        "participants": list(participants),
        "messages": messages
    }

# Only queries from customer_df
query_ids = customer_df["tweet_id"].unique()

conversations = {}
missing_queries = []

for query_id in query_ids:
    if query_id not in tweet_lookup:
        missing_queries.append(query_id)
        continue

    conversations[query_id] = {
        "query": clean_text(tweet_lookup[query_id]["text"]),
        "conversation": build_conversation(query_id)
    }

# Statistics
total_messages = sum(
    len(x["conversation"]["messages"])
    for x in conversations.values()
)

total_participants = sum(
    len(x["conversation"]["participants"])
    for x in conversations.values()
)

print("Rows in customer_df:", len(customer_df))
print("Unique customer queries:", len(query_ids))
print("Conversations created:", len(conversations))
print("Queries missing from dataset:", len(missing_queries))
print("Total messages:", total_messages)
print("Total participant entries:", total_participants)

# Save
with open("./conversations.json", "w", encoding="utf-8") as f:
    json.dump(conversations, f, indent=2, ensure_ascii=False)




