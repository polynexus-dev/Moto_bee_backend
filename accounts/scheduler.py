import logging
from django.core.management import call_command
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)


def flush_expired_tokens():
    logger.info('[Scheduler] Running flushexpiredtokens...')
    call_command('flushexpiredtokens')
    logger.info('[Scheduler] Done.')


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), 'default')

    scheduler.add_job(
        flush_expired_tokens,
        trigger='interval',
        days=15,                        # runs every 15 days
        id='flush_expired_tokens',
        replace_existing=True,
    )

    logger.info('[Scheduler] Starting...')
    scheduler.start()