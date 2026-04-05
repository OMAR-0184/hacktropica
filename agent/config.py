"""
Configuration & LLM factory for Cognimap.

All tunables live here so they can be overridden via env vars
(COGNIMAP_* and selected direct aliases like GOOGLE_API_KEY).
"""

from __future__ import annotations

from functools import lru_cache

import os
from typing import Any
from pathlib import Path
from pydantic import AliasChoices, Field
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
    # Supports either COGNIMAP_GOOGLE_API_KEY or direct GOOGLE_API_KEY.
    google_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("COGNIMAP_GOOGLE_API_KEY", "GOOGLE_API_KEY"),
    )
    tavily_api_key: str = ""
    root_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    tutor_model: str = "gemini-2.5-flash"
    quiz_model: str = "gemini-2.5-flash"
    curator_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    evaluator_model: str = "gemini-2.5-flash"
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


def get_llm(node_type: str = "root", temperature: float | None = None) -> Any:
    """Build a chat model instance tailored to the node type."""
    s = get_settings()

    model_map = {
        "root": s.root_model,
        "tutor": s.tutor_model,
        "quiz": s.quiz_model,
        "curator": s.curator_model,
        "evaluator": s.evaluator_model,
        "bridge": s.bridge_model,
    }

    model_name = model_map.get(node_type, s.root_model)
    model_name_normalized = str(model_name or "").strip().lower()
    effective_temp = temperature if temperature is not None else s.temperature

    # Route Gemini models through Google provider.
    if model_name_normalized.startswith("gemini"):
        api_key = str(s.google_api_key or "").strip() or str(os.getenv("GOOGLE_API_KEY", "")).strip()
        if not api_key:
            raise RuntimeError(
                f"GOOGLE_API_KEY is required for node_type='{node_type}' using model '{model_name}'."
            )
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency 'langchain-google-genai'. Install it to use Gemini models."
            ) from exc
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=effective_temp,
            google_api_key=api_key,
        )

    # Default provider: Hugging Face Inference Endpoint
    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        huggingfacehub_api_token=s.huggingface_api_token,
        temperature=effective_temp,
        task="text-generation",
        do_sample=True,
    )
    return ChatHuggingFace(llm=llm)
