"""
Configuration & LLM factory for Cognimap.

All tunables live here so they can be overridden via env vars
(COGNIMAP_OPENAI_API_KEY, COGNIMAP_MODEL_NAME, etc.).
"""

from __future__ import annotations

from functools import lru_cache

import os
from pathlib import Path
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {
        "env_prefix": "COGNIMAP_",
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    huggingface_api_token: str = ""
    tavily_api_key: str = ""
    root_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    tutor_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    curator_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    evaluator_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    bridge_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"

    temperature: float = 0.4

    mastery_threshold: float = 0.6
    max_remediation: int = 3

    max_subtopics: int = 6
    micro_subtopics: int = 3
    tree_min_children: int = 2
    tree_max_children: int = 4
    max_tree_depth: int = 4

    # ── Live Search ───────────────────────────────────────────
    search_max_articles: int = 5
    search_max_videos: int = 3
    search_max_courses: int = 3

    llm_max_retries: int = 3
    llm_retry_delay: float = 1.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


def get_llm(node_type: str = "root", temperature: float | None = None) -> ChatHuggingFace:
    """Build a ChatHuggingFace instance from current settings tailored to the node."""
    s = get_settings()
    
    model_map = {
        "root": s.root_model,
        "tutor": s.tutor_model,
        "curator": s.curator_model,
        "evaluator": s.evaluator_model,
        "bridge": s.bridge_model,
    }
    
    model_name = model_map.get(node_type, s.root_model)
    
    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        huggingfacehub_api_token=s.huggingface_api_token,
        temperature=temperature if temperature is not None else s.temperature,
        task="text-generation",
        do_sample=True,
    )
    return ChatHuggingFace(llm=llm)
