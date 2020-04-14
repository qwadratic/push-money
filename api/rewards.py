from flask import Blueprint
from flask_restx import Api, Resource, reqparse, fields, inputs
from mintersdk.sdk.wallet import MinterWallet

from helpers.misc import uuid
from minter.helpers import TxDeeplink

bp_rewards = Blueprint('rewards', __name__, url_prefix='/api/rewards')
api = Api(bp_rewards, title="Rewards API", description="YYY Rewards API")
ns_campaign = api.namespace('campaign', description='Campaign operations')
ns_action = api.namespace('action', description='User actions')

action_mdl = ns_campaign.model('Action', {
    'type': fields.String(enum=['youtube-subscribe', 'youtube-comment', 'youtube-like']),
    'reward': fields.Float,
    'channel': fields.String(),
    'video': fields.String,
})
parser_campaign_create = reqparse.RequestParser(trim=True, bundle_errors=True)
parser_campaign_create.add_argument('name', required=True)
parser_campaign_create.add_argument('coin', required=True)
parser_campaign_create.add_argument('budget', type=float, required=True)
parser_campaign_create.add_argument('action', type=action_mdl, required=True)

parser_action = reqparse.RequestParser(trim=True, bundle_errors=True)
parser_action.add_argument('type', required=True)
parser_action.add_argument('video')
parser_action.add_argument('videos', action='append')
parser_action.add_argument('channel')
parser_action.add_argument('duration', type=float)


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
            'times_completed': 3,
            'value_spent': 0.15,
            'coin': 'POPE',
            'action': {
                'type': 'youtube-subscribe',
                'channel': 'ChannelName',
                'reward': 0.05,
            }
        }


@ns_action.route('/')
class Action(Resource):

    @ns_action.expect(parser_action)
    def post(self):
        args = parser_action.parse_args()
        print('#####', args)
        return {
            'rewards': [{
                'amount': 0.01,
                'coin': 'POPE',
                'text': 'Todo: Subscribe',
                'status': 'todo',
                'type': 'youtube-subscribe',
                'channel': 'UC7Rtksgq4z0c9uqqz2JDWNQ',
            }, {
                'amount': 0.02,
                'coin': 'POPE',
                'text': 'Pending: Like',
                'status': 'pending',
                'type': 'youtube-like',
                'video': 'iWHRfPuJPnc',
                'push_link': '2SwMph'
            }, {
                'amount': 0.03,
                'coin': 'POPE',
                'text': 'Done: Comment',
                'status': 'done',
                'type': 'youtube-comment',
                'video': 'iWHRfPuJPnc',
            }]
        }
