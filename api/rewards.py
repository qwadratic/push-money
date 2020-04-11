from flask import Blueprint
from flask_restx import Api, Resource, reqparse, fields, inputs
from mintersdk.sdk.wallet import MinterWallet

from helpers.misc import uuid
from minter.helpers import TxDeeplink

bp_rewards = Blueprint('rewards', __name__, url_prefix='/api/rewards')
api = Api(bp_rewards, title="Rewards API", description="YYY Rewards API")
ns_campaign = api.namespace('campaign', description='Campaign operations')


action_mdl = ns_campaign.model('Action', {
    'type': fields.String(enum=['youtube-subscribe', 'youtube-comment', 'youtube-like']),
    'reward': fields.Float,
    'channel': fields.String(discriminator='123'),
    'video': fields.String,
})
parser_campaign_create = reqparse.RequestParser(trim=True, bundle_errors=False)
parser_campaign_create.add_argument('name', required=True)
parser_campaign_create.add_argument('coin', required=True)
parser_campaign_create.add_argument('budget', type=float, required=True)
parser_campaign_create.add_argument('actions', type=action_mdl, action='append', required=True)


@ns_campaign.route('/')
class Campaign(Resource):

    @ns_campaign.expect(parser_campaign_create)
    def post(self):
        args = parser_campaign_create.parse_args()
        budget = args['budget']
        coin = args['coin']
        campaign_id = uuid()
        wallet = MinterWallet.create()
        deeplink = TxDeeplink.create('send', to=wallet['address'], value=float(budget), coin=coin)
        return {
            'id': campaign_id,
            'address': wallet['address'],
            'deeplink': deeplink.mobile
        }


@ns_campaign.route('/<campaign_id>/')
class CampaignOne(Resource):

    def get(self, campaign_id):
        return {
            'id': campaign_id,
            'name': 'Campaign Name',
            'address': 'Mx...',
            'budget': 10,
            'balance': 9.85,
            'total_spent': 0.15,
            'coin': 'POPE',
            'actions': [
                {
                    'type': 'youtube-subscribe',
                    'channel': 'ChannelName',
                    'reward': 0.02,
                    'times_completed': 5,
                    'value_spent': 0.1
                },
                {
                    'type': 'youtube-like',
                    'video': 'adfKGG2',
                    'reward': 0.01,
                    'times_completed': 5,
                    'value_spent': 0.05
                }
            ]
        }
