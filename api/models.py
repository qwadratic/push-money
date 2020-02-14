from datetime import datetime

import peeweedbevolve
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from peewee import CharField, TextField, PostgresqlDatabase, Model, IntegerField, ForeignKeyField, BooleanField
from playhouse.postgres_ext import JSONField, DateTimeField

from config import DB_USER, DB_NAME

database = PostgresqlDatabase(DB_NAME, user=DB_USER)


class BaseModel(Model):
    class Meta:
        database = database


class PushWallet(BaseModel):
    link_id = CharField()
    sent_from = CharField(null=True)
    address = CharField()
    mnemonic = TextField()

    campaign_id = IntegerField(null=True)
    virtual_balance = CharField(null=True, default='0')
    seen = BooleanField(default=False)

    sender = TextField(null=True)
    recipient = TextField(null=True)
    password_hash = TextField(null=True)

    customization_setting_id = IntegerField(null=True)

    def auth(self, password):
        if self.password_hash is None:
            return True
        return password is not None and pbkdf2_sha256.verify(password, self.password_hash)


class PushCampaign(BaseModel):
    company = TextField(null=True)
    wallet_link_id = CharField()
    cost_pip = CharField()
    status = CharField()
    password = TextField(null=True)
    # status:
    # - open - создана
    # - paid - оплачена
    # - progress - рассылка идет
    # - completed - рассылка окончена
    # - closed - "лишние" деньги возвращены отправителю


class OrderHistory(BaseModel):
    timestamp = DateTimeField(default=datetime.utcnow)

    provider = CharField()
    product_id = CharField()

    price_pip = CharField()
    address_from = CharField()
    address_to = CharField()

    contact = CharField(null=True)
    notified = BooleanField(default=False)


class WebhookEvent(BaseModel):
    timestamp = DateTimeField()
    provider = CharField()
    event_id = CharField()
    event_data = JSONField()


class Recipient(BaseModel):
    created_at = DateTimeField(default=datetime.utcnow)
    sent_at = DateTimeField(null=True)
    opened_at = DateTimeField(null=True)
    linked_at = DateTimeField(null=True)

    campaign_id = ForeignKeyField(PushCampaign, backref='recipients')
    wallet_link_id = CharField()
    email = CharField()
    name = TextField()
    amount_pip = CharField()

    target = CharField(null=True)

    @property
    def target_route(self):
        y_food_url = '/food,grocery/%D0%AF%D0%BD%D0%B4%D0%B5%D0%BA%D1%81.%D0%95%D0%B4%D0%B0/certificate/'
        b2ph_url = '/mobile'
        return y_food_url if self.target == 'y-food' else b2ph_url if self.target == 'bip2ph' else ''


class UserImage(BaseModel):
    filename = TextField()
    created_at = DateTimeField(default=datetime.utcnow)


class CustomizationSetting(BaseModel):
    logo_image_id = IntegerField(null=True)
    head_text = TextField(null=True)
    background_name = CharField(null=True)
    animation_name = CharField(null=True)
    animation_text = TextField(null=True)
    target_shop = CharField(null=True)

    email_image_id = IntegerField(null=True)
    email_text = TextField(null=True)


def create_tables():
    with database:
        database.create_tables([
            PushWallet, PushCampaign, WebhookEvent, Recipient,
            OrderHistory, UserImage, CustomizationSetting])
