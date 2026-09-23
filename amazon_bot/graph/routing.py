from amazon_bot.config import get_settings


def after_classification(state):
    if not state.get("is_relevant") or state.get("confidence", 0) < get_settings().escalation_confidence:
        return "escalate"
    return "retrieve"


def after_review(state):
    review = state.get("review_result")
    if review and review.approved:
        return "finalize"
    if state.get("iteration_count", 0) >= get_settings().max_review_iterations:
        return "finalize"
    return "refine"
