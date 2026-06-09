"""Task queue factory."""
from __future__ import annotations

from app.config import get_settings
from app.jobs.base import TaskQueue
from app.jobs.inprocess import InProcessQueue

_queue: TaskQueue | None = None


def get_queue() -> TaskQueue:
    """Process-wide singleton so the worker pool is shared."""
    global _queue
    if _queue is None:
        settings = get_settings()
        if settings.queue_backend == "inprocess":
            _queue = InProcessQueue(max_workers=settings.worker_concurrency)
        else:
            # Add: if settings.queue_backend == "celery": return CeleryQueue()
            raise ValueError(f"Unknown QUEUE_BACKEND: {settings.queue_backend}")
    return _queue
