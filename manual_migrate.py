from datetime import datetime

from flask_security.utils import hash_password
from social_flask_peewee.models import FlaskStorage

from api.models import Merchant, User, Brand, Shop, Product, Category, MerchantImage, base_models, Role, UserRole, \
    WebhookEvent, UserImage, CustomizationSetting, OrderHistory, PushCampaign, PushWallet, Recipient, db
from config import ADMIN_PASS
from minter.utils import to_pip
from providers.gift import gift_order_create
from providers.giftery import GifteryAPIClient
from wsgi import app

security = app.extensions['security']
datastore = security.datastore
database = db.database


def create_gift(merchant, brand):
    food = Category.get(slug='food')
    yfood = Shop.create(
        name='Яндекс.Еда (GIFT)', integrated=True, active=True, in_moderation=False,
        brand=brand, merchant=merchant, category=food)

    for price in [1000, 2000, 3000]:
        slug = f'y{price}'
        resp = gift_order_create(slug)
        price_bip = to_pip(resp['price_bip'])
        p = Product.create(
            title='Яндекс.Еда (GIFT)', slug=slug, price_fiat=price * 100, currency='RUB',
            price_pip=price_bip, coin='BIP', shop=yfood, product_type='certificate')


def create_giftery(merchant, brand=None):
    client = GifteryAPIClient()
    categories = client.get_categories()

    giftery_cat = {}
    for cat in categories:
        if cat['code'] in ['new', 'popular', '']:
            continue
        mdl = Category.create(
            slug=cat['code'].lower(), title=cat['title'], title_en=cat['title_en'])
        giftery_cat[cat['id']] = mdl

    products = client.get_products()
    for product in products:
        shop = Shop.create(
            name=product['title'], integrated=True, active=True, in_moderation=False,
            merchant=merchant, description=product['brief'], brand=brand)
        categories = list(filter(None, [giftery_cat.get(c_id) for c_id in product['categories']]))
        if not categories:
            continue
        shop.category = categories[0]
        shop.save()
        if not product['faces']:
            continue

        if product['faces'][0] == 0:
            p = Product.create(
                shop=shop,
                active=True,
                currency='RUB',
                title=product['title'],
                description=product['disclaimer'],
                slug=product['id'],
                price_fiat_min=int(product['face_min']),
                price_fiat_max=int(product['face_max']),
                price_fiat_step=int(product['face_step']),
                product_type='certificate')
            MerchantImage.create(product=p, url=product['image_url'])

        p = Product.create(
            shop=shop,
            active=True,
            currency='RUB',
            title=product['title'],
            description=product['disclaimer'],
            slug=product['id'],
            price_list_fiat=[int(price) * 100 for price in product['faces']],
            product_type='certificate')
        MerchantImage.create(product=p, url=product['image_url'])


@database.atomic()
def update_certificates():
    admin = User.get(email='admin')
    manual = Merchant.create(user=admin)

    gift = Brand.create(name='GIFT', merchant=manual)
    # gratz = Brand.create(name='Gratz', merchant=manual)
    create_giftery(manual)
    create_gift(manual, gift)


@database.atomic()
def create_admin():
    anonymous_role, _ = Role.get_or_create(name='anonymous')
    super_role, _ = Role.get_or_create(name='superuser')
    user_role, _ = Role.get_or_create(name='user')
    user = datastore.get_user('admin')
    if user:
        return
    datastore.create_user(
        first_name='Admin',
        email='admin',
        password=hash_password(ADMIN_PASS),
        confirmed_at=datetime.utcnow(),
        roles=[user_role, super_role])


@database.atomic()
def recreate_schema():
    service_models = [WebhookEvent, UserImage]
    app_models = [CustomizationSetting, OrderHistory, PushCampaign, PushWallet, Recipient]
    shop_models = [Merchant, Brand, Shop, Product, Category, MerchantImage]
    user_models = [UserRole, Role, User, FlaskStorage.user]

    to_process = service_models + app_models + shop_models + user_models

    database.drop_tables(to_process)
    database.evolve(ignore_tables=[m for m in all_models if m in to_process] + base_models)

    # create_admin()


if __name__ == '__main__':
    from peeweedbevolve import all_models
    # recreate_schema()
    update_certificates()
    # biptophone = Brand.create(name='BipToPhone', merchant=manual)
    # timeloop = Brand.create(name='Timeloop', merchant=manual)
    # unu = Brand.create(name='UNU', merchant=manual)
    # db.database.drop_tables(all_models)





