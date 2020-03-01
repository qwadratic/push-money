from datetime import datetime

import peeweedbevolve
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

virtual_models = [mdl for mdl in peeweedbevolve.all_models if mdl._meta.table_name in base_models]
service_models = [WebhookEvent, UserImage]
app_models = [CustomizationSetting, OrderHistory, PushCampaign, PushWallet, Recipient]
shop_models = [Merchant, Brand, Shop, Product, Category, MerchantImage]
user_models = [UserRole, Role, User, FlaskStorage.user]


def create_gift(merchant, brand):
    food = Category.get(slug='food')
    yfood = Shop.create(
        name='Яндекс.Еда (GIFT)', integrated=True, active=True, in_moderation=False,
        brand=brand, merchant=merchant, category=food)

    for price in [1000, 2000, 3000]:
        slug = f'y{price}'
        resp = gift_order_create(slug)
        if isinstance(resp, str):
            continue
        price_bip = to_pip(resp['price_bip'])
        p = Product.create(
            title='Яндекс.Еда (GIFT)', slug=slug, price_fiat=price, currency='RUB',
            price_pip=price_bip, coin='BIP', shop=yfood, product_type='certificate', active=True)


def create_giftery(merchant, brand=None):
    to_merge = {'spa': 'beauty', 'cafe': 'food', 'electronics': 'tech'}
    rename = {'hobby': 'entertainment', 'accs': 'accesories'}

    client = GifteryAPIClient()
    categories = client.get_categories()

    giftery_cat = {}
    giftery_slugs = {}
    for cat in categories:
        slug = cat['code'] = cat['code'].lower()
        if slug in ['new', 'popular', '']:
            continue
        if slug in rename:
            cat['code'] = rename[slug]

        mdl = Category.create(
            slug=cat['code'], title=cat['title'], title_en=cat['title_en'])
        giftery_cat[cat['id']] = mdl
        giftery_slugs[cat['code']] = mdl

    products = client.get_products()
    to_del = set()
    for product in products:
        shop = Shop.create(
            name=product['title'], integrated=True, active=True, in_moderation=False,
            merchant=merchant, description=product['brief'], brand=brand)
        categories = list(filter(None, [giftery_cat.get(c_id) for c_id in product['categories']]))

        if categories:
            slugs = [c.slug for c in categories]
            for merge_slug in to_merge:
                if merge_slug in slugs:
                    slugs.remove(merge_slug)
                    slugs.append(to_merge[merge_slug])
                    to_del.add(merge_slug)
            slugs = sorted(list(set(slugs)))
            if len(slugs) == 1:
                final = giftery_slugs[slugs[0]]
            else:
                final, _ = Category.get_or_create(
                    slug=','.join(slugs),
                    title=giftery_slugs[slugs[0]].title,
                    title_en=giftery_slugs[slugs[0]].title_en)
            shop.category = final
            shop.save()

        active = bool(product['faces'])

        if active and product['faces'][0] == 0:
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
            continue
        p = Product.create(
            shop=shop,
            active=active,
            currency='RUB',
            title=product['title'],
            description=product['disclaimer'],
            slug=product['id'],
            price_list_fiat=[int(price) for price in product['faces']],
            product_type='certificate')
        MerchantImage.create(product=p, url=product['image_url'])
    to_del = [giftery_slugs[s] for s in to_del]
    for cat in to_del:
        cat.delete_instance()

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
def recreate_schema(to_process=None):
    database.drop_tables(to_process or peeweedbevolve.all_models)
    database.evolve(ignore_tables=virtual_models)

    # create_admin()


if __name__ == '__main__':
    recreate_schema(shop_models)
    update_certificates()
    # biptophone = Brand.create(name='BipToPhone', merchant=manual)
    # timeloop = Brand.create(name='Timeloop', merchant=manual)
    # unu = Brand.create(name='UNU', merchant=manual)
    # db.database.drop_tables(all_models)





