from amazon_bot.graph import nodes
from amazon_bot.graph.workflow import build_graph


def test_graph_completes_with_mocked_llm_and_retrieval(monkeypatch):
    class FakeLLM:
        def invoke(self, prompt):
            if "Review this" in prompt:
                return type("Result", (), {
                    "approved": True, "score": 0.95, "issues": [],
                    "suggestions": [], "requires_human": False,
                    "model_dump": lambda self: {
                        "approved": True, "score": 0.95, "issues": [],
                        "suggestions": [], "requires_human": False,
                    },
                    "model_dump_json": lambda self: "{}",
                })()
            return type("Result", (), {"content": "Your delivery is delayed; please check the carrier tracking page."})()

    class FakeStructured:
        def invoke(self, prompt):
            if "Review this" in prompt:
                return type("Review", (), {
                    "approved": True, "score": 0.95, "issues": [],
                    "suggestions": [], "requires_human": False,
                    "model_dump": lambda self: {
                        "approved": True, "score": 0.95, "issues": [],
                        "suggestions": [], "requires_human": False,
                    },
                    "model_dump_json": lambda self: "{}",
                })()
            return type("Classification", (), {
                "is_relevant": True, "intent": "delivery_issue",
                "confidence": 0.93, "reason": "delivery query",
                "model_dump": lambda self: {
                    "is_relevant": True, "intent": "delivery_issue",
                    "confidence": 0.93, "reason": "delivery query",
                },
            })()

    monkeypatch.setattr(nodes, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(nodes, "structured_llm", lambda schema: FakeStructured())
    monkeypatch.setattr(nodes, "retrieve_candidates", lambda query: [])
    result = build_graph().invoke({"query": "where is my package?", "user_id": "demo"})
    assert result["final_response"]["status"] == "completed"
    assert result["intent"] == "delivery_issue"
