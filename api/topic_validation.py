from __future__ import annotations

from typing import Any


_DISALLOWED_HINTS = {
    "weapon",
    "explosive",
    "bomb",
    "malware",
    "phishing",
    "fraud",
    "self harm",
    "suicide",
}

_SUGGESTED_TOPICS = [
    "Python fundamentals",
    "Data structures",
    "SQL basics",
    "System design for beginners",
]


async def validate_learning_topic_with_moderation(topic: str) -> dict[str, Any]:
    """
    Lightweight topic validation shim used by the learning router.

    Returns a stable response contract:
    - valid topic: {"status": "valid_learning_topic", "normalized_topic": "..."}
    - invalid topic: {"status": "invalid_learning_topic", "code": "...", "message": "...", "suggestions": [...]}
    """
    normalized = " ".join(topic.split()).strip()
    if not normalized:
        return {
            "status": "invalid_learning_topic",
            "code": "EMPTY_TOPIC",
            "message": "Topic cannot be empty.",
            "suggestions": _SUGGESTED_TOPICS,
        }

    lowered = normalized.lower()
    if any(bad in lowered for bad in _DISALLOWED_HINTS):
        return {
            "status": "invalid_learning_topic",
            "code": "UNSAFE_TOPIC",
            "message": "This topic is not allowed for learning guidance.",
            "suggestions": _SUGGESTED_TOPICS,
        }

    return {
        "status": "valid_learning_topic",
        "normalized_topic": normalized,
    }
