import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

# One job per region, firing at the UTC equivalent of midnight in the region's center timezone.
# EMEA (center UTC+1):     23:00 UTC
# AMERICAS (center UTC-7): 07:00 UTC
# APAC (center UTC+9):     15:00 UTC
_BIRTHDAY_JOBS = [
    ("EMEA",     23, "birthday_check_emea"),
    ("AMERICAS",  7, "birthday_check_americas"),
    ("APAC",     15, "birthday_check_apac"),
]


class BotScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=pytz.utc)

    def add_birthday_jobs(self, callback) -> None:
        for region, hour, job_id in _BIRTHDAY_JOBS:
            self.scheduler.add_job(
                callback,
                trigger=CronTrigger(hour=hour, minute=0),
                id=job_id,
                name=f"Birthday Check ({region})",
                args=[region],
                replace_existing=True,
                misfire_grace_time=300,
            )
        logger.info("Birthday jobs registered: EMEA@23:00, AMERICAS@07:00, APAC@15:00 UTC")

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
