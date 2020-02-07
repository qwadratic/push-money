from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


# рассылочная джоба:
#   - проверяет оплаты и стартует оплаченные кампании
#   - рассылает емейлы