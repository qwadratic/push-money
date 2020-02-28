from datetime import datetime

import peeweedbevolve
from flask_security import RoleMixin, UserMixin
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from peewee import CharField, TextField, IntegerField, ForeignKeyField, BooleanField
from playhouse.flask_utils import FlaskDB
from playhouse.postgres_ext import JSONField, DateTimeField


db = FlaskDB()


class PasswordProtectedModel(db.Model):
    password_hash = TextField(null=True)

    def auth(self, password):
        if self.password_hash is None:
            return True
        return password is not None and pbkdf2_sha256.verify(password, self.password_hash)


class PushWallet(PasswordProtectedModel):
    link_id = CharField()
    sent_from = CharField(null=True)
    address = CharField()
    mnemonic = TextField()

    virtual_balance = CharField(null=True, default='0')
    seen = BooleanField(default=False)

    sender = TextField(null=True)
    recipient = TextField(null=True)

    campaign_id = IntegerField(null=True)
    customization_setting_id = IntegerField(null=True)


class PushCampaign(PasswordProtectedModel):
    company = TextField(default='Unknown Company')
    wallet_link_id = CharField()
    cost_pip = CharField()

    # status:
    # - open - создана
    # - paid - оплачена
    # - progress - рассылка идет
    # - completed - рассылка окончена
    # - closed - остаток денег возвращен отправителю
    status = CharField()

    customization_setting_id = IntegerField(null=True)


class OrderHistory(db.Model):
    timestamp = DateTimeField(default=datetime.utcnow)

    provider = CharField()
    product_id = CharField()

    price_pip = CharField()
    address_from = CharField()
    address_to = CharField()

    contact = CharField(null=True)
    notified = BooleanField(default=False)


class WebhookEvent(db.Model):
    timestamp = DateTimeField(default=datetime.utcnow)
    provider = CharField()
    event_id = CharField()
    event_data = JSONField()


class Recipient(db.Model):
    created_at = DateTimeField(default=datetime.utcnow)
    sent_at = DateTimeField(null=True)
    opened_at = DateTimeField(null=True)
    linked_at = DateTimeField(null=True)

    campaign_id = ForeignKeyField(PushCampaign, backref='recipients')
    wallet_link_id = CharField()
    email = CharField()
    name = TextField()
    amount_pip = CharField()

    target_shop = CharField(null=True)

    @property
    def target_route(self):
        y_food_url = '/food,grocery/%D0%AF%D0%BD%D0%B4%D0%B5%D0%BA%D1%81.%D0%95%D0%B4%D0%B0/certificate/'
        b2ph_url = '/mobile'
        return y_food_url if self.target_shop == 'y-food' else b2ph_url if self.target_shop == 'bip2ph' else ''


class UserImage(db.Model):
    filename = TextField()
    created_at = DateTimeField(default=datetime.utcnow)


class CustomizationSetting(db.Model):
    logo_image_id = IntegerField(null=True)
    head_text = TextField(null=True)
    background_name = CharField(null=True)
    animation_name = CharField(null=True)
    animation_text = TextField(null=True)

    email_image_id = IntegerField(null=True)
    email_head_text = TextField(null=True)
    email_body_text = TextField(null=True)
    email_button_text = TextField(null=True)
    email_subject_text = TextField(null=True)

    target_shop = CharField(null=True)
    only_target = BooleanField(default=False)


class Role(db.Model, RoleMixin):
    name = CharField(unique=True)
    description = TextField(null=True)


class User(db.Model, UserMixin):
    username = CharField(null=True)
    email = CharField(null=True)
    password = CharField(null=True)
    active = BooleanField(default=True)
    confirmed_at = DateTimeField(null=True)

    @property
    def is_anonymous(self):
        return self.has_role('anonymous')

    @property
    def is_authenticated(self):
        return not self.is_anonymous

    def __str__(self):
        return f'<User {self.id} ({"LOGGED_OUT" if self.is_anonymous else "LOGGED IN"})>'


class UserRole(db.Model):
    user = ForeignKeyField(User, related_name='roles')
    role = ForeignKeyField(Role, related_name='users')
    name = property(lambda self: self.role.name)
    description = property(lambda self: self.role.description)
