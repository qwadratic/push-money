from api.app_init import app_init
from jobs.scheduler import scheduler


app = app_init()
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True, port=8000)
