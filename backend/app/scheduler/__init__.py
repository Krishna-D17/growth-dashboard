"""
SocialScope Scheduler Module
Integrates APScheduler with FastAPI and CollectionService.
"""
from app.scheduler.scheduler import start_scheduler, shutdown_scheduler, get_scheduler

__all__ = ["start_scheduler", "shutdown_scheduler", "get_scheduler"]
