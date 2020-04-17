from flask import Blueprint
from flask_restx import Api, Resource, reqparse, fields, inputs
from mintersdk.sdk.wallet import MinterWallet

from api.models import RewardCampaign
from helpers.misc import uuid
from minter.helpers import TxDeeplink, to_pip, to_bip
from providers.mscan import MscanAPI

bp_rewards = Blueprint('rewards', __name__, url_prefix='/api/rewards')
api = Api(bp_rewards, title="Rewards API", description="YYY Rewards API")
ns_campaign = api.namespace('campaign', description='Campaign operations')
ns_action = api.namespace('action', description='User actions')

action_mdl = ns_campaign.model('Action', {
    'type': fields.String(enum=['youtube-subscribe', 'youtube-comment', 'youtube-like', 'youtube-watch']),
    'reward': fields.Float,
    'link': fields.String,
})
parser_campaign_create = reqparse.RequestParser(trim=True, bundle_errors=True)
parser_campaign_create.add_argument('name', required=True)
parser_campaign_create.add_argument('coin', required=True)
parser_campaign_create.add_argument('count', type=float, required=True)
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
        count = args['count']
        coin = args['coin']
        name = args['name']
        action = args['action']
        campaign_id = uuid()
        wallet = MinterWallet.create()
        action_reward = float(action['reward'])
        fees = 0
        deeplink = TxDeeplink.create('send', to=wallet['address'], value=action_reward * count + fees, coin=coin)
        RewardCampaign.create(
            link_id=campaign_id,
            address=wallet['address'],
            mnemonic=wallet['mnemonic'],
            name=name,
            count=count,
            coin=coin,
            action_type=action['type'],
            action_reward=to_pip(action_reward),
            action_params=action)
        return {
            'id': campaign_id,
            'address': wallet['address'],
            'deeplink': deeplink.mobile
        }


@ns_campaign.route('/<campaign_id>/')
class CampaignOne(Resource):

    def get(self, campaign_id):
        campaign = RewardCampaign.get_or_none(link_id=campaign_id)
        if not campaign:
            return {}
        balances = MscanAPI.get_balance(campaign.address)['balance']
        campaign_balance = float(to_bip(balances.get(campaign.coin, '0')))
        times_completed = 0
        reward = float(to_bip(campaign.action_reward))
        value_spent = times_completed * reward
        return {
            'id': campaign.link_id,
            'name': campaign.name,
            'address': campaign.address,
            'count': campaign.count,
            'coin': campaign.coin,
            'balance': campaign_balance,
            'times_completed': times_completed,
            'value_spent': value_spent,
            'action': {
                'type': campaign.action_type,
                'link': campaign.action_params['link'],
                'reward': reward,
            }
        }


@ns_action.route('/')
class Action(Resource):

    @ns_action.expect(parser_action)
    def post(self):
        args = parser_action.parse_args()
        return {
            'rewards': [{
                'id': 'fasdadg',
                'amount': 0.01,
                'coin': 'POPE',
                'text': 'Todo: Subscribe',
                'status': 'todo',
                'type': 'youtube-subscribe',
                'channel': 'UC7Rtksgq4z0c9uqqz2JDWNQ',
            }, {
                'id': 'asGEW',
                'amount': 0.02,
                'coin': 'POPE',
                'text': 'Pending: Like',
                'status': 'pending',
                'type': 'youtube-like',
                'video': 'iWHRfPuJPnc',
                'push_link': '2SwMph'
            }, {
                'id': 'XZBE00',
                'amount': 0.03,
                'coin': 'POPE',
                'text': 'Done: Comment',
                'status': 'done',
                'type': 'youtube-comment',
                'video': 'iWHRfPuJPnc',
            }]
        }
