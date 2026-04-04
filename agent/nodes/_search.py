"""
_search — Async web search utility for the Curator node.

Uses DuckDuckGo via the `ddgs` package (free, no API key) to find real
articles, videos, and courses for a given learning subtopic.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ddgs import DDGS

from agent.config import get_settings

logger = logging.getLogger(__name__)


def _build_query(topic: str, subtopic: str, suffix: str = "") -> str:
    """Build a focused search query string."""
    base = f"{subtopic} {topic}" if topic and topic.lower() != subtopic.lower() else subtopic
    return f"{base} {suffix}".strip()


async def _async_search_text(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Asynchronous DuckDuckGo text search."""
    try:
        # ddgs>=9 exposes a synchronous API; offload to a worker thread.
        def _run() -> list[dict[str, Any]]:
            with DDGS(timeout=10) as ddgs:
                return ddgs.text(query, max_results=max_results)

        raw = await asyncio.to_thread(_run)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
            if r.get("href")
        ]
    except Exception as exc:
        logger.warning("DuckDuckGo text search failed for %r: %s", query, exc)
        return []


async def _async_search_videos(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """Asynchronous DuckDuckGo video search."""
    try:
        # ddgs>=9 exposes a synchronous API; offload to a worker thread.
        def _run() -> list[dict[str, Any]]:
            with DDGS(timeout=10) as ddgs:
                return ddgs.videos(query, max_results=max_results)

        raw = await asyncio.to_thread(_run)
        results = []
        for r in raw:
            url = r.get("content", "") or r.get("embed_url", "")
            if not url:
                continue
            results.append({
                "title": r.get("title", ""),
                "url": url,
                "snippet": r.get("description", ""),
            })
        return results
    except Exception as exc:
        logger.warning("DuckDuckGo video search failed for %r: %s", query, exc)
        return []


async def search_articles(
    topic: str, subtopic: str, max_results: int | None = None
) -> list[dict[str, str]]:
    """Search for tutorial articles and documentation."""
    settings = get_settings()
    n = max_results or settings.search_max_articles
    query = _build_query(topic, subtopic, "tutorial guide explanation")
    return await _async_search_text(query, n)


async def search_videos(
    topic: str, subtopic: str, max_results: int | None = None
) -> list[dict[str, str]]:
    """Search for YouTube / educational videos."""
    settings = get_settings()
    n = max_results or settings.search_max_videos
    query = _build_query(topic, subtopic, "tutorial")
    return await _async_search_videos(query, n)


async def search_courses(
    topic: str, subtopic: str, max_results: int | None = None
) -> list[dict[str, str]]:
    """Search for courses on major platforms (Coursera, Udemy, Khan Academy, edX)."""
    settings = get_settings()
    n = max_results or settings.search_max_courses
    query = _build_query(topic, subtopic, "online course free")
    return await _async_search_text(query, n)


async def search_all(
    topic: str, subtopic: str
) -> dict[str, list[dict[str, str]]]:
    """Run all three searches concurrently and return combined results."""
    articles, videos, courses = await asyncio.gather(
        search_articles(topic, subtopic),
        search_videos(topic, subtopic),
        search_courses(topic, subtopic),
    )
    return {
        "articles": articles,
        "videos": videos,
        "courses": courses,
    }
