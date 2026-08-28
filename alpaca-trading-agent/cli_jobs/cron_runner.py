"""
Asynchronous cron task runner for periodic CLI job execution.

This module provides the `CronRunner` class to schedule, execute, and monitor
periodic tasks such as position monitoring and portfolio rebalancing using `asyncio`.
"""

import asyncio
import inspect
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Type alias for scheduled job functions (supports both sync and async callables)
JobCallable = Callable[[], Union[Any, Awaitable[Any]]]


class CronRunner:
    """
    Simple asynchronous cron-like task scheduler for periodic jobs.

    Attributes:
        _jobs (Dict[str, Dict[str, Any]]): Internal job registry.
        _running (bool): Execution state flag.
        _tasks (List[asyncio.Task]): Background worker tasks for scheduled jobs.
    """

    def __init__(self) -> None:
        """Initialize the CronRunner scheduler."""
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._running: bool = False
        self._tasks: List[asyncio.Task[None]] = []

    def add_job(
        self,
        name: str,
        callable_func: JobCallable,
        interval_seconds: int,
    ) -> None:
        """
        Register a new periodic job.

        Args:
            name: Unique identifier name for the job.
            callable_func: Function or coroutine function to execute.
            interval_seconds: Delay interval in seconds between job executions.
        """
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be a positive integer.")

        self._jobs[name] = {
            "name": name,
            "callable": callable_func,
            "interval_seconds": interval_seconds,
            "last_run": None,
            "next_run": None,
            "run_count": 0,
            "last_error": None,
        }
        logger.info("Added job '%s' scheduled every %d seconds.", name, interval_seconds)

    async def _run_job_loop(self, job_name: str) -> None:
        """
        Worker loop for executing a single registered job on its schedule.

        Args:
            job_name: Name of the registered job to run.
        """
        job = self._jobs[job_name]
        interval = job["interval_seconds"]

        logger.info("Started worker loop for job '%s'", job_name)

        while self._running:
            now = datetime.now(timezone.utc)
            job["last_run"] = now.isoformat()
            job["next_run"] = (now + timedelta(seconds=interval)).isoformat()

            logger.info("Executing job '%s' (Run #%d)...", job_name, job["run_count"] + 1)
            try:
                callable_func = job["callable"]
                if inspect.iscoroutinefunction(callable_func):
                    await callable_func()
                else:
                    callable_func()

                job["run_count"] += 1
                job["last_error"] = None
                logger.info("Job '%s' completed successfully.", job_name)
            except Exception as exc:
                job["last_error"] = str(exc)
                logger.exception("Error occurred while executing job '%s': %s", job_name, exc)

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("Job loop for '%s' was cancelled.", job_name)
                break

    async def start(self) -> None:
        """
        Start the scheduler and launch worker loops for all registered jobs using asyncio.

        This method blocks until stopped or cancelled if awaited continuously,
        or spawns background tasks for all scheduled jobs.
        """
        if self._running:
            logger.warning("CronRunner is already running.")
            return

        if not self._jobs:
            logger.warning("No jobs registered in CronRunner before starting.")

        self._running = True
        self._tasks = []

        logger.info("Starting CronRunner scheduler with %d registered jobs.", len(self._jobs))

        for job_name in self._jobs:
            task = asyncio.create_task(self._run_job_loop(job_name))
            self._tasks.append(task)

    def stop(self) -> None:
        """
        Stop the scheduler and cancel all running job tasks.
        """
        if not self._running:
            logger.warning("CronRunner is not currently running.")
            return

        logger.info("Stopping CronRunner scheduler...")
        self._running = False

        for task in self._tasks:
            if not task.done():
                task.cancel()

        self._tasks.clear()
        logger.info("CronRunner stopped.")

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieve current status, execution counts, and schedule details for all registered jobs.

        Returns:
            Dict[str, Any]: Dictionary summarizing scheduler state and individual job details:
                - is_running: Scheduler active status.
                - total_jobs: Total registered job count.
                - jobs: Dict mapping job name to status details (last_run, next_run, run_count, last_error).
        """
        jobs_summary: Dict[str, Dict[str, Any]] = {}
        for name, job in self._jobs.items():
            jobs_summary[name] = {
                "interval_seconds": job["interval_seconds"],
                "last_run": job["last_run"],
                "next_run": job["next_run"],
                "run_count": job["run_count"],
                "last_error": job["last_error"],
            }

        return {
            "is_running": self._running,
            "total_jobs": len(self._jobs),
            "jobs": jobs_summary,
        }
