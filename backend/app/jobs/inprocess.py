"""In-process task queue — a thread pool that runs the pipeline.

Good enough for single-node dev/demo. For horizontal scale, replace with a
Celery queue (separate worker processes) without touching the pipeline: both
ultimately call `orchestrator.run_analysis`.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from app.jobs.base import TaskQueue

log = logging.getLogger("app.jobs")


class InProcessQueue(TaskQueue):
    def __init__(self, max_workers: int = 1):
        # YOLO inference holds the GIL only briefly (work happens in native/
        # torch threads), and we keep concurrency low to avoid GPU contention.
        self._pool = ThreadPoolExecutor(
            max_workers=max(1, max_workers), thread_name_prefix="pipeline"
        )

    def enqueue(self, job_id: str) -> None:
        log.info("enqueue job %s", job_id)
        self._pool.submit(self._run, job_id)

    @staticmethod
    def _run(job_id: str) -> None:
        # Imported lazily so importing the queue never drags in torch/ultralytics.
        from app.pipeline.orchestrator import run_analysis

        try:
            run_analysis(job_id)
        except Exception:  # pragma: no cover - defensive; orchestrator self-reports
            log.exception("job %s crashed", job_id)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
