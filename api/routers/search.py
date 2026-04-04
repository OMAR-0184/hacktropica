
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.routers.auth import get_current_user
from api.database.models import User
from api.schemas.learning import SearchResponse, SearchResult
from agent.nodes._search import search_articles, search_videos, search_courses, search_all

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def live_search(
    current_user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    type: str = Query(
        default="all",
        description="Type of results: articles, videos, courses, or all",
    ),
    max_results: int = Query(default=5, ge=1, le=10, description="Max results per category"),
):
    """
    Live search for learning resources.

    Searches the web in real-time using DuckDuckGo and returns structured
    results from educational platforms, YouTube, and general web sources.
    """
    topic = ""

    if type == "articles":
        results = await search_articles(topic, q, max_results=max_results)
        return SearchResponse(
            query=q,
            type="articles",
            results=[SearchResult(**r) for r in results],
        )
    elif type == "videos":
        results = await search_videos(topic, q, max_results=max_results)
        return SearchResponse(
            query=q,
            type="videos",
            results=[SearchResult(**r) for r in results],
        )
    elif type == "courses":
        results = await search_courses(topic, q, max_results=max_results)
        return SearchResponse(
            query=q,
            type="courses",
            results=[SearchResult(**r) for r in results],
        )
    else:
        # "all" — run all searches concurrently
        all_results = await search_all(topic, q)
        combined = []
        for category, items in all_results.items():
            for item in items:
                combined.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    category=category,
                ))
        return SearchResponse(
            query=q,
            type="all",
            results=combined,
        )
