from typing import Dict, Any, List
import logging
from uuid import uuid4
from amazon_bot.graph.workflow import workflow
from amazon_bot.schemas import ConversationTurn

logger = logging.getLogger(__name__)

def process_chat(query: str, user_id: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        state = workflow.invoke({
            "query": query,
            "user_id": user_id,
            "history": [ConversationTurn(**turn) for turn in history],
        })
        return {"status": "success", "state": state}
    except Exception as error:
        request_id = uuid4().hex[:12]
        logger.exception("Workflow failed request_id=%s", request_id)
        return {"status": "error", "error": str(error), "request_id": request_id}
