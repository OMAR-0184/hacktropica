"""Compatibility exports for task queue client (formerly bullmq_client)."""

from __future__ import annotations

from api.services.task_queue import (
    ALLOWED_JOBS,
    QUEUE_NAME,
    BullMQClient,
    TaskQueueClient,
    close_queue_client,
    get_queue_client,
    start_queue_client,
)

__all__ = [
    "ALLOWED_JOBS",
    "QUEUE_NAME",
    "BullMQClient",
    "TaskQueueClient",
    "close_queue_client",
    "get_queue_client",
    "start_queue_client",
]
