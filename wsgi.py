from api.app_init import app_init
from jobs.scheduler import scheduler

scheduler.start()
app = app_init()


if __name__ == '__main__':

    app.run(debug=True, port=8000)
