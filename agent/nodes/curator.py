"""
curator_node — Curates REAL external resources via live web search.

Instead of asking the LLM to hallucinate URLs, this node:
1. Performs real DuckDuckGo searches for articles, videos, and courses
2. Passes the search results to the LLM for ranking and curation
3. Returns verified, clickable URLs
"""

from __future__ import annotations

import logging
from typing import Any

from agent.nodes._llm_call import invoke_llm_json
from agent.nodes._search import search_all
from agent.state import CognimapState

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a learning resource curator. You will receive REAL search results
from the web (articles, videos, and courses).

Your job is to:
1. Select the MOST relevant and highest-quality resources for learning about
   the given subtopic within the broader topic.
2. For each selected resource, write a short 1-sentence description of WHY
   it is useful for the learner.
3. Only include resources that are directly relevant to the subtopic.

Return ONLY a JSON object with these keys:
- "articles": list of selected articles (each a dict with "title", "url", "description")
- "videos": list of selected videos (each a dict with "title", "url", "description")
- "courses": list of selected courses (each a dict with "title", "url", "description")
- "references": list of 1-2 additional general reading suggestions (strings)
"""

_DEFAULTS = {
    "articles": [],
    "videos": [],
    "courses": [],
    "references": [],
}


def _format_search_results(results: dict[str, list[dict[str, str]]]) -> str:
    """Format raw search results into a readable string for the LLM."""
    sections = []
    for category, items in results.items():
        if not items:
            continue
        lines = [f"\n=== {category.upper()} ==="]
        for i, item in enumerate(items, 1):
            lines.append(
                f"{i}. Title: {item['title']}\n"
                f"   URL: {item['url']}\n"
                f"   Snippet: {item.get('snippet', 'N/A')}"
            )
        sections.append("\n".join(lines))
    return "\n".join(sections) if sections else "(No search results found)"


async def curator_node(state: CognimapState) -> dict[str, Any]:
    """Curate learning resources using live web search + LLM ranking."""
    topic = state.get("topic", "")
    current = state["current_node"]

    # ── Step 1: Live web search ───────────────────────────────
    logger.info("[curator] Searching web for: %s / %s", topic, current)
    search_results = await search_all(topic, current)

    total_results = sum(len(v) for v in search_results.values())
    logger.info("[curator] Found %d total results across all categories", total_results)

    # ── Step 2: LLM ranks and curates the real results ────────
    if total_results > 0:
        formatted = _format_search_results(search_results)
        curator_content = await invoke_llm_json(
            node_type="curator",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Broader topic: {topic}\n"
                        f"Current subtopic: {current}\n\n"
                        f"Here are REAL search results from the web:\n{formatted}\n\n"
                        "Select and rank the best resources. Use ONLY the URLs "
                        "provided above — do NOT invent new ones."
                    ),
                },
            ],
            required_keys=["articles", "videos", "references"],
            defaults=_DEFAULTS,
        )
    else:
        # Fallback: no search results, return empty curated content
        logger.warning("[curator] No search results found, returning empty content")
        curator_content = dict(_DEFAULTS)

    # Keep payload compact for checkpoint/history stability.
    curator_content["search_summary"] = {
        "articles_found": len(search_results.get("articles", [])),
        "videos_found": len(search_results.get("videos", [])),
        "courses_found": len(search_results.get("courses", [])),
    }

    lesson = dict(state.get("lesson", {}))
    lesson["curator_content"] = curator_content

    return {"lesson": lesson}
