from langgraph.graph import END, START, StateGraph
from amazon_bot.graph.nodes import (
    classify_query, retrieve, rerank_node, load_user_context,
    generate_answer, review_answer, refine_answer, finalize,
)
from amazon_bot.graph.routing import after_classification, after_review
from amazon_bot.graph.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("classify_query", classify_query)
    graph.add_node("retrieve_candidates", retrieve)
    graph.add_node("rerank_candidates", rerank_node)
    graph.add_node("load_user_context", load_user_context)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("review_answer", review_answer)
    graph.add_node("refine_answer", refine_answer)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "classify_query")
    graph.add_conditional_edges("classify_query", after_classification, {
        "retrieve": "retrieve_candidates", "escalate": "finalize",
    })
    graph.add_edge("retrieve_candidates", "rerank_candidates")
    graph.add_edge("rerank_candidates", "load_user_context")
    graph.add_edge("load_user_context", "generate_answer")
    graph.add_edge("generate_answer", "review_answer")
    graph.add_conditional_edges("review_answer", after_review, {
        "finalize": "finalize", "refine": "refine_answer",
    })
    graph.add_edge("refine_answer", "review_answer")
    graph.add_edge("finalize", END)
    return graph.compile()


workflow = build_graph()
