import logging
from datetime import datetime

import peeweedbevolve
from flask_security.utils import hash_password
from social_flask_peewee.models import FlaskStorage

from api.models import Merchant, User, Brand, Shop, Product, Category, MerchantImage, base_models, Role, UserRole, \
    WebhookEvent, UserImage, CustomizationSetting, OrderHistory, PushCampaign, PushWallet, Recipient, db
from config import ADMIN_PASS
from minter.helpers import to_pip
from providers.gift import gift_order_create
from providers.giftery import GifteryAPIClient
from providers.gratz import gratz_product_list, gratz_order_create
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
            title=f'{price} RUB',
            slug=slug,
            price_fiat=price,
            currency='RUB',
            price_pip=price_bip,
            coin='BIP',
            shop=yfood,
            product_type='certificate',
            active=True)


def create_gratz(merchant, brand):
    gratz_products, _ = gratz_product_list()
    categories = {c.slug: c for c in Category.select()}
    gratz_shops = {s.name: s for s in Shop.select().where(Shop.brand == brand)}

    for cat_slug, shops in gratz_products.items():
        cat_model = categories.get(cat_slug)
        if cat_slug == 'gas' and not cat_model:
            cat_model = Category.create(slug='gas', title='АЗС', title_en='Gas')
        if not cat_model:
            logging.info(f'Bad category slug {cat_slug} (GRATZ)')
            continue
        for shop_name, products in shops.items():
            shop_model = gratz_shops.get(shop_name)
            if not shop_model:
                shop_model = Shop.create(
                    name=f'{shop_name} (GRATZ)',
                    integrated=True, active=True, in_moderation=False,
                    merchant=merchant, category=cat_model, brand=brand)
                gratz_shops[shop_name] = shop_model

            for product in products:
                response = gratz_order_create(product['slug'].split('-')[1])
                price_pip = to_pip(response['price_bip'])
                Product.create(
                    product_type='certificate',
                    active=True,
                    price_fiat=product['value'],
                    price_pip=price_pip,
                    coin='BIP',
                    currency='UAH',
                    slug=product['slug'],
                    title=f"{product['value']} UAH",
                    shop=shop_model)


def create_giftery(merchant, brand=None):
    to_merge = {'spa': 'beauty', 'cafe': 'food', 'electronics': 'tech'}
    rename = {'hobby': 'entertainment', 'accs': 'accesories'}

    client = GifteryAPIClient()
    categories = client.get_categories()

    giftery_cat = {}
    giftery_slugs = {c.slug: c for c in Category.select()}
    for cat in categories:
        slug = cat['code'] = cat['code'].lower()
        if slug in ['new', 'popular', '']:
            continue
        if slug in rename:
            cat['code'] = rename[slug]
        mdl = giftery_slugs.get(cat['code'])
        if not mdl:
            mdl = Category.create(
                slug=cat['code'],
                title=cat['title'],
                title_en=cat['title_en'])
            giftery_slugs[cat['code']] = mdl
        giftery_cat[cat['id']] = mdl
        giftery_slugs[cat['code']] = mdl

    products = client.get_products()
    to_del = set()
    shop_mdls = {s.name: s for s in Shop.select().where(Shop.brand.is_null())}
    for product in products:
        shop = shop_mdls.get(product['title'])
        if not shop:
            shop = Shop.create(
                name=product['title'],
                integrated=True,
                active=True,
                in_moderation=False,
                merchant=merchant,
                description=product['brief'],
                brand=brand)
            shop_mdls[shop.name] = shop
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
                slug=f"giftery-{product['id']}",
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
            slug=f"giftery-{product['id']}",
            price_list_fiat=[int(price) for price in product['faces']],
            product_type='certificate')
        MerchantImage.create(product=p, url=product['image_url'])
    to_del = [giftery_slugs[s] for s in to_del]
    for cat in to_del:
        cat.delete_instance()


@database.atomic()
def update_certificates():
    admin = User.get(email='admin')
    manual, _ = Merchant.get_or_create(user=admin)

    gift, _ = Brand.get_or_create(name='GIFT', merchant=manual)
    gratz, _ = Brand.get_or_create(name='Gratz', merchant=manual)

    create_giftery(manual)
    create_gift(manual, gift)
    create_gratz(manual, gratz)


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


@database.atomic()
def recreate_full_catalog():
    recreate_schema(shop_models)
    update_certificates()


@database.atomic()
def recreate_products(brand_name):
    giftery_flag = brand_name == 'Giftery'
    brand = Brand.get_or_none(name=brand_name)
    if not brand and not giftery_flag:
        return
    cond = Shop.brand == brand if not giftery_flag else Shop.brand.is_null()
    if giftery_flag:
        MerchantImage.delete().execute()

    Product \
        .delete() \
        .where(
            Product.shop.in_(Shop.select().where(cond))) \
        .execute()

    admin = User.get(email='admin')
    manual = Merchant.get(user=admin)
    if brand_name == 'Giftery':
        create_giftery(manual)
    if brand_name == 'GIFT':
        create_gift(manual, brand)
    if brand_name == 'Gratz':
        create_gratz(manual, brand)


if __name__ == '__main__':
    recreate_full_catalog()
    # recreate_products('Giftery')
    # biptophone = Brand.create(name='BipToPhone', merchant=manual)
    # timeloop = Brand.create(name='Timeloop', merchant=manual)
    # unu = Brand.create(name='UNU', merchant=manual)
    # db.database.drop_tables(all_models)





