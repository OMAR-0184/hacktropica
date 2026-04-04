# Async web search utility for the Curator node.
# Uses Tavily via the `tavily-python` package to find core
# articles, videos, and courses for a given learning subtopic.

from __future__ import annotations

import asyncio
import logging
from typing import Any

from tavily import AsyncTavilyClient

from agent.config import get_settings

logger = logging.getLogger(__name__)


def _build_query(topic: str, subtopic: str, suffix: str = "") -> str:
    "Build a focused search query string."
    base = f"{subtopic} {topic}" if topic and topic.lower() != subtopic.lower() else subtopic
    return f"{base} {suffix}".strip()


async def _tavily_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    "Asynchronous Tavily search."
    settings = get_settings()
    if not settings.tavily_api_key:
        logger.warning("No TAVILY_API_KEY found in settings.")
        return []
    
    try:
        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(query=query, search_depth="basic", max_results=max_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in response.get("results", [])
            if r.get("url")
        ]
    except Exception as exc:
        logger.warning("Tavily search failed for %r: %s", query, exc)
        return []


async def search_articles(
    topic: str, subtopic: str, max_results: int | None = None
) -> list[dict[str, str]]:
    "Search for tutorial articles and documentation."
    settings = get_settings()
    n = max_results or settings.search_max_articles
    query = _build_query(topic, subtopic, "tutorial guide explanation")
    return await _tavily_search(query, n)


async def search_videos(
    topic: str, subtopic: str, max_results: int | None = None
) -> list[dict[str, str]]:
    "Search for YouTube / educational videos."
    settings = get_settings()
    n = max_results or settings.search_max_videos
    query = _build_query(topic, subtopic, "youtube video tutorial")
    return await _tavily_search(query, n)


async def search_courses(
    topic: str, subtopic: str, max_results: int | None = None
) -> list[dict[str, str]]:
    "Search for courses on major platforms (Coursera, Udemy, Khan Academy, edX)."
    settings = get_settings()
    n = max_results or settings.search_max_courses
    query = _build_query(topic, subtopic, "online course free")
    return await _tavily_search(query, n)


async def search_all(
    topic: str, subtopic: str
) -> dict[str, list[dict[str, str]]]:
    "Run all three searches concurrently and return combined results."
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
