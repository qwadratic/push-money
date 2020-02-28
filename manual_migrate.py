from api.models import Merchant, User, Brand, Shop, Product, ShopCategory, Category, db, MerchantImage
from minter.utils import to_pip
from providers.gift import gift_order_create
from providers.giftery import GifteryAPIClient
from wsgi import app

admin = User.get(email='admin')

manual = Merchant.create(user=admin)

biptophone = Brand.create(name='BipToPhone', merchant=manual)
timeloop = Brand.create(name='Timeloop', merchant=manual)
unu = Brand.create(name='UNU', merchant=manual)
# gratz = Brand.create(name='Gratz', merchant=manual)
gift = Brand.create(name='GIFT', merchant=manual)


def create_gift():
    yfood = Shop.create(
        name='Яндекс.Еда (GIFT)', integrated=True, active=True, in_moderation=False,
        brand=gift, merchant=manual)
    food = Category.get(slug='food')
    ShopCategory.create(shop=yfood, category=food)

    for price in [1000, 2000, 3000]:
        slug = f'y{price}'
        resp = gift_order_create(slug)
        price_bip = to_pip(resp['price_bip'])
        p = Product.create(
            title='Сертификат Яндекс.Еда', slug=slug, price_fiat=price * 100, currency='RUB',
            price_pip=price_bip, coin='BIP', shop=yfood)


def create_giftery():
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
    unsorted = Category.create(slug='unsorted', title='Несортированное', title_en='Unsorted')
    for product in products:
        shop = Shop.create(
            name='Яндекс.Еда (GIFT)', integrated=True, active=True, in_moderation=False,
            merchant=manual, description=product['brief'])
        categories = [giftery_cat.get(c_id) or unsorted for c_id in product['categories']]
        for cat in categories:
            ShopCategory.create(shop=shop, category=cat)
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
                price_fiat_min=int(product['face_min']) * 100,
                price_fiat_max=int(product['face_max']) * 100,
                price_fiat_step=int(product['face_step']) * 100)
            MerchantImage.create(product=p, url=product['image_url'])

        p = Product.create(
            shop=shop,
            active=True,
            currency='RUB',
            title=product['title'],
            description=product['disclaimer'],
            slug=product['id'],
            price_list_fiat=[int(price) * 100 for price in product['faces']])
        MerchantImage.create(product=p, url=product['image_url'])


if __name__ == '__main__':
    with app.app_context():
        with db.database.atomic():
            create_giftery()
            create_gift()


