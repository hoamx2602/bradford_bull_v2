"""Task queue abstraction.

`enqueue(job_id)` schedules `orchestrator.run_analysis(job_id)`. The in-process
implementation runs it on a thread pool; a Celery implementation would `.delay()`
a task that calls the same function. Callers never see the difference.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class TaskQueue(ABC):
    @abstractmethod
    def enqueue(self, job_id: str) -> None:
        ...

    def shutdown(self) -> None:  # optional override
        ...
