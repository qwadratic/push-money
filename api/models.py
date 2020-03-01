from datetime import datetime

import peeweedbevolve
from flask import url_for
from flask_security import RoleMixin, UserMixin
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from peewee import CharField, TextField, IntegerField, ForeignKeyField, BooleanField
from playhouse.flask_utils import FlaskDB
from playhouse.postgres_ext import JSONField, DateTimeField, IPField

from minter.utils import to_bip

base_models = [
    'basemodel', 'passwordprotectedmodel',
    'peeweeassociationmixin', 'peeweenoncemixin',
    'peeweecodemixin', 'peeweeusermixin', 'peeweepartialmixin'
]
db = FlaskDB()


class PasswordProtectedModel(db.Model):
    password_hash = TextField(null=True)

    def auth(self, password):
        if self.password_hash is None:
            return True
        return password is not None and pbkdf2_sha256.verify(password, self.password_hash)


class Role(db.Model, RoleMixin):
    name = CharField(unique=True)
    description = TextField(null=True)


class User(db.Model, UserMixin):
    username = CharField(null=True)
    email = CharField(null=True)
    password = CharField(null=True)
    active = BooleanField(default=True)
    confirmed_at = DateTimeField(null=True)
    last_login_at = DateTimeField(null=True)
    current_login_at = DateTimeField(null=True)
    last_login_ip = IPField(null=True)
    current_login_ip = IPField(null=True)
    login_count = IntegerField(null=True)

    @property
    def is_anonymous(self):
        return self.has_role('anonymous') or not self.roles

    @property
    def is_authenticated(self):
        return not self.is_anonymous

    def __str__(self):
        return f"{self.username or self.id} anonymous={self.is_anonymous}"


class UserRole(db.Model):
    user = ForeignKeyField(User, related_name='roles')
    role = ForeignKeyField(Role, related_name='users')
    name = property(lambda self: self.role.name)
    description = property(lambda self: self.role.description)

    def __str__(self):
        return f'role:{self.name}'


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
    filename = TextField(null=True)
    url = TextField()
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


class Merchant(db.Model):
    user = ForeignKeyField(User, backref='merch')
    address = CharField(null=True)
    mnemonic = TextField(null=True)
    balance_pip = CharField(default='0')
    blocked_balance_pip = CharField(default='0')


class Category(db.Model):
    title = CharField()
    title_en = CharField()
    slug = CharField(unique=True)

    @property
    def icon_url(self):
        return db._app.config['BASE_URL'] + url_for('upload.icons', content_type='category', object_name=self.slug)


class Brand(db.Model):
    name = CharField()
    merchant = ForeignKeyField(Merchant, related_name='brands')


class Shop(db.Model):
    deleted = BooleanField(default=False)
    integrated = BooleanField(default=False)
    active = BooleanField(default=False)
    in_moderation = BooleanField(default=True)

    name = CharField()
    description = TextField(null=True)

    brand = ForeignKeyField(Brand, related_name='shops', null=True)
    merchant = ForeignKeyField(Merchant, related_name='shops')
    category = ForeignKeyField(Category, related_name='shops', null=True)

    @property
    def slug(self):
        return str(self.id)

    @property
    def icon_url(self):
        return db._app.config['BASE_URL'] + url_for('upload.icons', content_type='shop', object_name=self.slug)

    @property
    def api_repr(self):
        active_products = self.products.where(Product.active & ~Product.deleted)
        if not active_products:
            return
        shop_repr = {
            'products': [product.api_repr for product in active_products],
        }
        price_type = 'fixed' if self.brand \
            else 'range' if ('price_list_fiat' not in shop_repr['products'][0]) \
                or (shop_repr['products'][0]['price_list_fiat'][0] == 0) \
            else 'list'
        shop_repr['price_type'] = price_type
        return shop_repr


class Product(db.Model):
    product_type = CharField()
    deleted = BooleanField(default=False)
    active = BooleanField(default=False)
    infinite = BooleanField(default=False)

    quantity = IntegerField(default=0, null=True)

    price_fiat = IntegerField(null=True)
    price_pip = CharField(null=True)

    price_list_fiat = JSONField(null=True)
    price_fiat_min = IntegerField(null=True)
    price_fiat_max = IntegerField(null=True)
    price_fiat_step = IntegerField(null=True)

    currency = CharField(null=False)
    coin = CharField(default='BIP')

    title = CharField()
    description = TextField(null=True)
    slug = CharField(null=True)

    shop = ForeignKeyField(Shop, related_name='products')

    @property
    def api_repr(self):
        price_patch = None
        if not self.price_list_fiat and self.price_fiat:
            price_patch = {
                'price_fiat': self.price_fiat,
                'price_bip': float(to_bip(self.price_pip)),
            }
        elif not self.price_list_fiat or (self.price_list_fiat and self.price_list_fiat[0] == 0):
            price_patch = {
                'price_fiat_min': self.price_fiat_min,
                'price_fiat_max': self.price_fiat_min,
                'price_fiat_step': self.price_fiat_step
            }
        elif self.price_list_fiat:
            price_patch = {
                'price_list_fiat': self.price_list_fiat
            }

        return {
            'slug': self.slug,
            'currency': self.currency,
            'coin': self.coin,
            'name': self.title,
            **price_patch
        }


class MerchantImage(UserImage):
    product = ForeignKeyField(Product, related_name='images', null=True, on_delete='CASCADE')
    shop = ForeignKeyField(Shop, related_name='images', null=True)
    brand = ForeignKeyField(Brand, related_name='images', null=True)
