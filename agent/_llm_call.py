"""
Shared LLM invocation wrapper with retry, validation, and fallback.

Every agent node should use `invoke_llm_json()` instead of calling the LLM
directly. This ensures consistent error handling, automatic retries on
transient failures, output validation against required keys, and sensible
fallbacks so the graph never crashes due to bad LLM output.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import json_repair

from agent.config import get_llm, get_settings

logger = logging.getLogger(__name__)

# Regex to strip markdown code fences that LLMs love to wrap JSON in
_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if present."""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _validate_and_fill(data: dict, required_keys: list[str], defaults: dict) -> dict:
    """
    Ensure all required_keys exist in data. Fill missing ones from defaults.
    Also coerce types where possible (e.g. score must be float).
    """
    for key in required_keys:
        if key not in data or data[key] is None:
            data[key] = defaults.get(key)
    return data


async def invoke_llm_json(
    *,
    node_type: str,
    messages: list[dict[str, str]],
    required_keys: list[str] | None = None,
    defaults: dict[str, Any] | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """
    Invoke an LLM and parse the response as JSON, with retry and validation.

    Args:
        node_type: Which LLM config to use (root, tutor, curator, evaluator, bridge).
        messages: Chat messages to send to the LLM.
        required_keys: Keys that must be present in the parsed output.
        defaults: Fallback values for missing/failed keys.
        temperature: Override temperature for this call.

    Returns:
        A validated dict. Never raises — always returns at least `defaults`.
    """
    settings = get_settings()
    max_retries = settings.llm_max_retries
    retry_delay = settings.llm_retry_delay
    required_keys = required_keys or []
    defaults = defaults or {}

    last_error: str | None = None
    last_raw: str | None = None

    for attempt in range(1, max_retries + 1):
        try:
            llm = get_llm(node_type=node_type, temperature=temperature)
            response = await llm.ainvoke(messages)
            raw = response.content.strip()
            last_raw = raw

            # Strip markdown fences
            cleaned = _strip_markdown_fences(raw)

            # Parse with json_repair (handles minor LLM JSON mistakes)
            data = json_repair.loads(cleaned)

            if not isinstance(data, dict):
                logger.warning(
                    "[%s] Attempt %d: LLM returned non-dict type %s, retrying...",
                    node_type, attempt, type(data).__name__,
                )
                last_error = f"Expected dict, got {type(data).__name__}"
                continue

            # Validate required keys
            missing = [k for k in required_keys if k not in data or data[k] is None]
            if missing and attempt < max_retries:
                logger.warning(
                    "[%s] Attempt %d: Missing keys %s, retrying...",
                    node_type, attempt, missing,
                )
                last_error = f"Missing keys: {missing}"
                continue

            # Fill any remaining gaps from defaults
            result = _validate_and_fill(data, required_keys, defaults)
            logger.info("[%s] Successfully parsed LLM output on attempt %d", node_type, attempt)
            return result

        except Exception as exc:
            last_error = str(exc)
            logger.error(
                "[%s] Attempt %d failed with error: %s",
                node_type, attempt, last_error,
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)  # Exponential backoff

    # All retries exhausted — return defaults
    logger.error(
        "[%s] All %d attempts failed. Last error: %s | Last raw output: %.500s",
        node_type, max_retries, last_error, last_raw or "(none)",
    )
    return dict(defaults)
