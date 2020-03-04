from flask import Blueprint, g, url_for
from flask_login import login_required
from flask_restx import Api, Resource

bp_merchant = Blueprint('merchant', __name__, url_prefix='/api/merchant')
api = Api(bp_merchant, title="Merchant API", description="YYY Merchant API")


@api.route('/brand/')
class BrandList(Resource):
    method_decorators = [login_required]

    def get(self):
        # brands = [mdl for mdl in Brand.select().where(Brand.user == g.user)]

        return [{
            'id': 1,
            'name': 'test',
            'logo_url': 'https://...' #url_for('upload.merchant_image', slug='brand-test')
        }]

    def post(self):
        return {'id': 1}


@api.route('/brand/<int:brand_id>/')
class Brand(Resource):
    method_decorators = [login_required]

    def get(self, brand_id):
        return {
            'id': 1,
            'name': 'test',
            'logo_url': 'https://...'
        }

    def put(self, brand_id):
        return {
            'id': 1,
        }

    def delete(self, brand_id):
        return {
            'id': 1,
        }


@api.route('/shop/')
class ShopList(Resource):
    method_decorators = [login_required]

    def get(self):
        return 'get shop list'

    def post(self):
        return 'shop create'


@api.route('/shop/<int:shop_id>/')
class Shop(Resource):
    method_decorators = [login_required]

    def get(self, shop_id):
        return 'shop info'

    def put(self, shop_id):
        return 'shop edit'

    def delete(self, shop_id):
        return 'shop delete'


@api.route('/shop/<int:shop_id>/product/')
class ProductList(Resource):
    method_decorators = [login_required]

    def get(self, shop_id):
        return 'get product list'

    def post(self, shop_id):
        return 'product create'


@api.route('/shop/<int:shop_id>/product/<int:product_id>')
class Product(Resource):
    method_decorators = [login_required]

    def get(self, shop_id, product_id):
        return 'get product'

    def put(self, shop_id, product_id):
        return 'product edit'

    def delete(self, shop_id, product_id):
        return 'product delete'
