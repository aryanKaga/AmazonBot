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


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "workflow", CompletedWorkflow())
    with api._sessions_lock:
        api._sessions.clear()
    yield TestClient(api.app)
    with api._sessions_lock:
        api._sessions.clear()


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


def test_chat_persists_conversation_by_session(client):
    first = client.post(
        "/chat",
        json={"query": "Where is my package?", "session_id": "session-a"},
    )
    second = client.post(
        "/chat",
        json={"query": "Is it delayed?", "session_id": "session-a"},
    )
    separate = client.post(
        "/chat",
        json={"query": "New conversation", "session_id": "session-b"},
    )

    assert first.status_code == second.status_code == separate.status_code == 200
    assert len(first.json()["conversation"]) == 2
    assert len(second.json()["conversation"]) == 4
    assert len(separate.json()["conversation"]) == 2
    assert second.json()["conversation"][0]["text"] == "Where is my package?"


def test_clear_session_removes_history(client):
    client.post("/chat", json={"query": "First", "session_id": "session-clear"})

    cleared = client.delete("/sessions/session-clear")
    after_clear = client.post(
        "/chat", json={"query": "After clear", "session_id": "session-clear"}
    )

    assert cleared.status_code == 200
    assert cleared.json() == {"status": "cleared", "session_id": "session-clear"}
    assert len(after_clear.json()["conversation"]) == 2


def test_workflow_failure_returns_gateway_error(client, monkeypatch):
    class FailingWorkflow:
        def invoke(self, state):
            raise RuntimeError("backend unavailable")

    monkeypatch.setattr(api, "workflow", FailingWorkflow())

    response = client.post("/chat", json={"query": "Try again"})

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
