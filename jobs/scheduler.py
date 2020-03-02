from apscheduler.schedulers.background import BackgroundScheduler

from config import DEV


class YYYScheduler(BackgroundScheduler):
    def scheduled_job(self, *args, disable_dev=False, **kwargs):
        if DEV and disable_dev:
            return lambda fn: fn
        return super().scheduled_job(*args, **kwargs)


scheduler = YYYScheduler(
    job_defaults={
        'misfire_grace_time': 5*60
    })
