"""
RAG-Anything configuration for Gemini 2.5 Flash.
Uses the same GEMINI_API_KEY from the project's .env file.
"""

import os
import numpy as np
from raganything import RAGAnythingConfig
from lightrag.llm.gemini import gemini_model_complete, gemini_embed
from lightrag.utils import wrap_embedding_func_with_attrs

# RAG-Anything config
rag_config = RAGAnythingConfig(
    working_dir="/app/storage",
    parser="mineru",
    parse_method="auto",
    enable_image_processing=True,
    enable_table_processing=True,
    enable_equation_processing=True,
)

# Gemini LLM function (text generation)
async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    return await gemini_model_complete(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("GEMINI_API_KEY"),
        model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
        **kwargs
    )

# Gemini Vision function (multimodal queries)
async def vision_model_func(
    prompt, system_prompt=None, history_messages=[],
    image_data=None, messages=None, **kwargs
) -> str:
    return await gemini_model_complete(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("GEMINI_API_KEY"),
        model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
        **kwargs
    )

# Gemini Embedding function
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))

@wrap_embedding_func_with_attrs(
    embedding_dim=EMBEDDING_DIM,
    max_token_size=2048,
    model_name=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
)
async def embedding_func(texts: list[str]) -> np.ndarray:
    return await gemini_embed(
        texts,
        api_key=os.getenv("GEMINI_API_KEY"),
        model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001"),
    )
