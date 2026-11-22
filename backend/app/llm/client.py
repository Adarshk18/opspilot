from functools import lru_cache
from openai import AsyncOpenAI
from app.core.config import get_settings


@lru_cache
def get_llm_client()->  AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=90,
        max_retries=0,
    )