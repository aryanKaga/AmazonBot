import json
import pytest
from fastapi.testclient import TestClient

from amazon_bot import api
from amazon_bot.human_bucket import create_ticket

class CompletedWorkflow:
    def invoke(self, state):
        return {
            "final_response": {
                "status": "completed",
                "answer": f"Answer for: {state['query']}",
            },
            "intent": "delivery_issue",
            "confidence": 0.93,
            "reranked_conversations": [],
            "review_result": {
                "approved": True,
                "score": 0.95,
                "issues": [],
                "suggestions": [],
                "requires_human": False,
            },
        }

class MockRedis:
    def __init__(self):
        self.data = {}
    def ping(self):
        return True
    def set(self, k, v, ex=None):
        self.data[k] = v
    def get(self, k):
        return self.data.get(k)
    def delete(self, k):
        self.data.pop(k, None)
    def hset(self, name, k, v):
        if name not in self.data:
            self.data[name] = {}
        self.data[name][k] = v
    def hget(self, name, k):
        return self.data.get(name, {}).get(k)
    def hgetall(self, name):
        return self.data.get(name, {})

class FakeJob:
    def __init__(self, task_id, result):
        self.id = task_id
        self.is_failed = False
        self.is_finished = True
        self.result = result

class FakeQueue:
    def enqueue(self, func, *args, **kwargs):
        res = func(*args, **kwargs)
        job = FakeJob("task-123", res)
        # Store in global so fetch can find it
        api._fake_jobs["task-123"] = job
        return job

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "workflow", CompletedWorkflow())
    
    mock_redis = MockRedis()
    monkeypatch.setattr(api, "get_redis", lambda: mock_redis)
    from amazon_bot import human_bucket
    monkeypatch.setattr(human_bucket, "get_redis", lambda: mock_redis)
    
    api._fake_jobs = {}
    monkeypatch.setattr(api, "get_queue", lambda: FakeQueue())
    
    def fake_job_fetch(task_id, connection):
        if task_id in api._fake_jobs:
            return api._fake_jobs[task_id]
        from rq.exceptions import NoSuchJobError
        raise NoSuchJobError()
        
    from rq.job import Job
    monkeypatch.setattr(Job, "fetch", fake_job_fetch)

    yield TestClient(api.app)

def test_health_and_frontend_are_available(client):
    health = client.get("/health")
    frontend = client.get("/")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert frontend.status_code == 200
    assert "<title>Amazon Bot Assistant</title>" in frontend.text

def test_chat_rejects_empty_query(client):
    response = client.post("/chat", json={"query": "", "session_id": "invalid"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "query"

def get_chat_response(client, query, session_id):
    post_res = client.post("/chat", json={"query": query, "session_id": session_id})
    assert post_res.status_code == 200
    task_id = post_res.json()["task_id"]
    return client.get(f"/chat/status/{task_id}")

def test_chat_persists_conversation_by_session(client):
    first = get_chat_response(client, "Where is my package?", "session-a")
    second = get_chat_response(client, "Is it delayed?", "session-a")
    separate = get_chat_response(client, "New conversation", "session-b")

    assert first.status_code == second.status_code == separate.status_code == 200
    assert len(first.json()["conversation"]) == 2
    assert len(second.json()["conversation"]) == 4
    assert len(separate.json()["conversation"]) == 2
    assert second.json()["conversation"][0]["text"] == "Where is my package?"

def test_clear_session_removes_history(client):
    get_chat_response(client, "First", "session-clear")
    cleared = client.delete("/sessions/session-clear")
    after_clear = get_chat_response(client, "After clear", "session-clear")

    assert cleared.status_code == 200
    assert cleared.json() == {"status": "cleared", "session_id": "session-clear"}
    assert len(after_clear.json()["conversation"]) == 2

def test_workflow_failure_returns_gateway_error(client, monkeypatch):
    class FailingWorkflow:
        def invoke(self, state):
            raise RuntimeError("backend unavailable")

    monkeypatch.setattr(api, "workflow", FailingWorkflow())
    from amazon_bot import tasks
    monkeypatch.setattr(tasks, "workflow", FailingWorkflow())
    
    post_res = client.post("/chat", json={"query": "Try again"})
    task_id = post_res.json()["task_id"]
    response = client.get(f"/chat/status/{task_id}")

    assert response.status_code == 502
    assert response.json()["detail"] == "workflow failed: backend unavailable"

def test_human_ticket_can_be_listed_and_claimed(client):
    ticket = create_ticket({"query": "Needs a human"})

    listed = client.get("/human-bucket")
    claimed = client.post(f"/human-bucket/{ticket['ticket_id']}/claim")
    missing = client.post("/human-bucket/HB-MISSING/claim")

    assert listed.status_code == 200
    assert any(item["ticket_id"] == ticket["ticket_id"] for item in listed.json()["tickets"])
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "claimed"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "human ticket not found"
