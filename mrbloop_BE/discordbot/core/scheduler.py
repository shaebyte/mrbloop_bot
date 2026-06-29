"""
Scheduler – beheert alle periodieke taken met APScheduler.

Birthday job draait elke minuut zodat elke user
om exact 00:15 lokale tijd wordt gefeliciteerd.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)


class BotScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=pytz.utc)

    def add_birthday_job(self, callback) -> None:
        self.scheduler.add_job(
            callback,
            trigger=CronTrigger(minute="*"),  # elke minuut
            id="birthday_check",
            name="Birthday Check (all timezones)",
            replace_existing=True,
            misfire_grace_time=30,
        )
        logger.info("Birthday job registered to run every minute (all timezones)")

    def add_event_reminder_job(self, callback) -> None:
        """Placeholder voor feature 2."""
        self.scheduler.add_job(
            callback,
            trigger=CronTrigger(minute="*/5"),
            id="event_reminder_check",
            name="Event Reminder Check",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info("Event reminder job registered (placeholder)")

    def start(self) -> None:
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
