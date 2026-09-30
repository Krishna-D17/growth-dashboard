import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.scheduler.jobs import run_scheduled_collections

logger = logging.getLogger("socialscope.scheduler")

_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Returns the single application BackgroundScheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
    return _scheduler


def start_scheduler() -> Optional[BackgroundScheduler]:
    """
    Initializes and starts the APScheduler background runner.
    Registers the scheduled collection tick job.
    Safe against multiple initialization calls.
    """
    if not settings.scheduler_enabled:
        logger.info("APScheduler disabled via SCHEDULER_ENABLED configuration.")
        return None

    scheduler = get_scheduler()
    if scheduler.running:
        logger.warning("APScheduler is already running.")
        return scheduler

    tick_minutes = settings.scheduler_tick_minutes
    scheduler.add_job(
        func=run_scheduled_collections,
        trigger=IntervalTrigger(minutes=tick_minutes),
        id="scheduled_profile_collection_job",
        name="Scheduled Social Media Profile Collection",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    logger.info(f"APScheduler started successfully with {tick_minutes}-minute tick interval.")
    return scheduler


def shutdown_scheduler() -> None:
    """Cleanly stops the APScheduler background runner if active."""
    global _scheduler
    if _scheduler and _scheduler.running:
        logger.info("Shutting down APScheduler...")
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
