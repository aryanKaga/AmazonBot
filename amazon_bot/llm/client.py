import logging
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from amazon_bot.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_llm():
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,
        max_retries=2,
    )
    logger.info("Initialized Gemini client for model %s", settings.gemini_model)
    return llm


def structured_llm(schema):
    return get_llm().with_structured_output(schema)
