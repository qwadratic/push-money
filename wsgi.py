from api.app_init import app_init
from config import DEV, APP_PORT
from jobs.scheduler import scheduler


app = app_init()
scheduler.app = app
scheduler.start()

if __name__ == '__main__':
    app.run(debug=DEV, port=APP_PORT)
