from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(
    job_defaults={
        'misfire_grace_time': 5*60
    })
