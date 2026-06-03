# coding: utf-8

import os

from lightrag.llm.openai import (
    openai_embed,
    openai_complete_if_cache,
)
import numpy as np


async def stub_embed(texts: list[str]) -> np.ndarray:
    """Stub embedding func which always returns 1 for every input."""
    return np.concatenate([np.ones((1, 1)) for _ in texts])


async def vllm_embed(texts: list[str], **kwargs) -> np.ndarray:
    return await openai_embed(
        texts,
        model=os.getenv("EMBEDDING_MODEL"),
        api_key=os.getenv("EMBEDDING_BINDING_API_KEY"),
        base_url=os.getenv("EMBEDDING_BINDING_HOST"),
        **kwargs,
    )


async def vllm_model_complete(prompt, system_prompt=None, history_messages=None, **kwargs) -> str:
    """LLM completion through vllm backend."""
    return await openai_complete_if_cache(
        model=os.getenv("LLM_MODEL"),
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("LLM_BINDING_API_KEY"),
        base_url=os.getenv("LLM_BINDING_HOST"),
        max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS")),
        **kwargs,
    )
