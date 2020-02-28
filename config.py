import os

import dotenv

dotenv.load_dotenv()

DEV = bool(int(os.environ.get('DEV')))
TESTNET = bool(int(os.environ.get('TESTNET')))
LOCAL = bool(int(os.environ.get('LOCAL')))

GOOGLE_CLIENT_KEY_FILENAME = 'gclient-keys.json'
MSCAN_APIKEY = os.environ.get('MSCAN_APIKEY')
BIP2PHONE_API_KEY = os.environ.get('BIP2PHONE_API_KEY')
GIFTERY_API_ID = os.environ.get('GIFTERY_API_ID')
GIFTERY_API_SECRET = os.environ.get('GIFTERY_API_SECRET')
GRATZ_API_KEY = os.environ.get('GRATZ_API_KEY')
UNU_API_KEY = os.environ.get('UNU_API_KEY')

BIP_WALLET = os.environ.get('BIP_WALLET')

SMTP_HOST = 'smtp-mail.outlook.com'
SMTP_PORT = 587
EMAIL_SENDER = "noreply@push.money"
EMAIL_PASS = os.environ.get('EMAIL_PASS')

GRATZ_OWNER_EMAIL = 'amperluxe@gmail.com'
DEV_EMAIL = 'ivan.d.kotelnikov@gmail.com'

ADMIN_PASS = os.environ.get('ADMIN_PASS')

DB_NAME = os.environ.get('{}DB_NAME'.format('DEV_' if DEV else ''))
DB_USER = os.environ.get('{}DB_USER'.format('DEV_' if DEV else ''))


class FlaskConfig:
    DATABASE = {
        'name': DB_NAME,
        'engine': 'peewee.PostgresqlDatabase',
        'user': DB_USER
    }
    FLASK_ADMIN_SWATCH = 'cyborg'

    BASE_URL = 'https://{}push.money'.format('dev.' if DEV else '')
    UPLOADED_IMAGES_DEST = 'content/user_images'
    UPLOADED_IMAGES_URL = BASE_URL + '/api/upload/'

    SECRET_KEY = os.environ.get('APP_SECRET_KEY')
    SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    SECURITY_LOGIN_URL = '/auth/login/'
    SECURITY_LOGOUT_URL = '/auth/logout/'
    # SECURITY_POST_LOGIN_VIEW = '/auth/login/email'
    # SECURITY_POST_LOGOUT_VIEW = '/admin/'

    SOCIAL_AUTH_PIPELINE = (
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.auth_allowed',
        'social_core.pipeline.social_auth.social_user',
        'social_core.pipeline.user.get_username',

        # Send a validation email to the user to verify its email address.
        # 'social_core.pipeline.mail.mail_validation',

        # Associates the current social details with another user account with
        # a similar email address.
        'social_core.pipeline.social_auth.associate_by_email',

        'social_core.pipeline.user.create_user',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
        'social_core.pipeline.user.user_details'
    )
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = not LOCAL
    SOCIAL_AUTH_LOGIN_REDIRECT_URL = 'https://yyy.cash'

    SOCIAL_AUTH_AUTHENTICATION_BACKENDS = (
        'social_core.backends.google.GoogleOAuth2',
        'social_core.backends.telegram.TelegramAuth',
        'social_core.backends.email.EmailAuth'
    )
    SOCIAL_AUTH_USER_MODEL = 'api.models.User'
    SOCIAL_AUTH_STORAGE = 'social_flask_peewee.models.FlaskStorage'
    SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = ['keep']

    SOCIAL_AUTH_TELEGRAM_BOT_TOKEN = os.environ.get('TG_TOKEN')
    SOCIAL_AUTH_TELEGRAM_LOGIN_REDIRECT_URL = '/' if DEV else 'https://yyy.cash'

    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_OAUTH_KEY')
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_OAUTH_SECRET')
    SOCIAL_AUTH_GOOGLE_OAUTH2_LOGIN_REDIRECT_URL = '/' if DEV else 'https://yyy.cash'

    SOCIAL_AUTH_EMAIL_FORM_URL = '/auth/login/email' if DEV else 'https://yyy.cash/'
    SOCIAL_AUTH_EMAIL_FORM_HTML = 'dev/login.html'
    SOCIAL_AUTH_EMAIL_LOGIN_REDIRECT_URL = '/' if DEV else 'https://yyy.cash'