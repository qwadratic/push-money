from pushmoney.app_init import app, app_init


app_init(app)


if __name__ == '__main__':
    app.run(debug=True)
