from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'run-daily-allocation': {
        'task': 'allocation.tasks.run_daily_allocation',
        'schedule': crontab(hour=7, minute=0),
    },
}