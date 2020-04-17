import logging

import requests
from urllib.parse import parse_qs, urlparse

from cachetools.func import ttl_cache
from flask import Blueprint
from flask_restx import Api, Resource, reqparse, fields
from flask_uploads import extension
from mintersdk.sdk.wallet import MinterWallet
from werkzeug.datastructures import FileStorage

from api.models import RewardCampaign, RewardIcon
from api.upload import images
from config import YOUTUBE_APIKEY
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
parser_campaign_create.add_argument('name', required=True, location='form')
parser_campaign_create.add_argument('action_coin', required=True, location='form')
parser_campaign_create.add_argument('count', type=float, required=True, location='form')
parser_campaign_create.add_argument('action_type', required=True, location='form')
parser_campaign_create.add_argument('action_reward', type=float, required=True, location='form')
parser_campaign_create.add_argument('action_link', required=True, location='form')
parser_campaign_create.add_argument('action_duration', required=False, location='form')
parser_campaign_create.add_argument('icon', location='files', type=FileStorage, required=True)

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
        coin = args['action_coin']
        name = args['name']
        action_type = args['action_type']
        action_reward = args['action_reward']
        action_link = args['action_link']
        action_duration = args['action_duration']

        action = {
            'type': action_type,
            'reward': action_reward,
            'link': action_link,
            'duration': action_duration
        }
        campaign_id = uuid()
        wallet = MinterWallet.create()
        action_reward = float(action['reward'])
        fees = 0
        deeplink = TxDeeplink.create('send', to=wallet['address'], value=action_reward * count + fees, coin=coin)

        icon_storage = args['icon']
        filename = images.save(icon_storage, name=f'{campaign_id}.{extension(icon_storage.filename)}')
        icon = RewardIcon.create(filename=filename, url=images.url(filename))
        RewardCampaign.create(
            link_id=campaign_id,
            address=wallet['address'],
            mnemonic=wallet['mnemonic'],
            name=name,
            count=count,
            coin=coin,
            action_type=action['type'],
            action_reward=to_pip(action_reward),
            action_params=action,
            icon=icon)
        return {
            'id': campaign_id,
            'address': wallet['address'],
            'deeplink': deeplink.web
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
            'icon_url': campaign.icon.url if campaign.icon else None,
            'action': {
                'type': campaign.action_type,
                'link': campaign.action_params['link'],
                'reward': reward,
            }
        }



ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE


@ttl_cache(ttl=24 * ONE_HOUR)
def get_channel_id(video_id):
    r = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
        'part': 'snippet',
        'id': video_id,
        'key': YOUTUBE_APIKEY
    })
    response = r.json()
    if not response['items']:
        return

    return response['items'][0]['snippet']['channelId']


def parse_video_id(url):
    parsed = urlparse(url)
    v = parse_qs(parsed.query).get('v')
    return v[0] if v else None


def parse_channel_id(url):
    path_parts = urlparse(url).path.split('/')
    if 'channel' not in path_parts or 'user' not in path_parts:
        return
    return path_parts[-1]


def get_campaigns_by_video_id(video_id):
    campaigns = {}
    for cmp in RewardCampaign.filter(
            action_type__in=['youtube-like', 'youtube-subscribe', 'youtube-watch']):

        link = cmp.action_params['link']
        if cmp.action_type == 'youtube-subscribe':
            if video_id not in link:
                channel_id = get_channel_id(video_id)
                if not channel_id or channel_id not in link:
                    continue
        if cmp.action_type in ['youtube-watch', 'youtube-like', 'youtube-comment']:
            if video_id not in link:
                continue

        # check is done
        campaigns.setdefault(cmp.action_type, [])
        campaigns[cmp.action_type].append(cmp)
    return campaigns


@ttl_cache(ttl=ONE_HOUR)
def get_available_rewards_video(video_id):
    if not video_id:
        return []
    campaigns = get_campaigns_by_video_id(video_id)
    rewards = {}
    for action_type, models in campaigns.items():
        rewards.setdefault(action_type, [])
        for cmp in models:
            params = {}
            if action_type == 'youtube-subscribe':
                params['channel'] = cmp.action_params['link']
            if action_type in ['youtube-watch', 'youtube-comment', 'youtube-like']:
                params['video'] = cmp.action_params['link']
            if 'duration' in cmp.action_params and action_type == 'youtube-watch':
                try:
                    casted_duration = float(cmp.action_params['duration'])
                except Exception:
                    continue
                params['duration'] = casted_duration

            rewards[action_type].append({
                'id': cmp.link_id,
                'amount': cmp.action_params['reward'],
                'coin': cmp.coin,
                'text': cmp.name,
                'type': cmp.action_type,
                **params
            })
    return rewards


@ns_action.route('/')
class Action(Resource):

    @ns_action.expect(parser_action)
    def post(self):
        args = parser_action.parse_args()
        # {
        #     'type': 'youtube-subscribe',
        #     'video': 'https://www.youtube.com/watch?v=a-2OE6TZw24',
        #     'videos': None,
        #     'channel': None,
        #     'duration': None
        # }
        logging.info(f'##### {args}')

        available_rewards = {}
        if args['video']:
            video_id = parse_video_id(args['video'])
            available_rewards = get_available_rewards_video(video_id)

        if args['type'] == 'youtube-watch' and 'youtube-watch' in available_rewards:
            duration = args['duration']
            for task in available_rewards['youtube-watch']:
                if duration >= task['duration']:
                    task['status'] = 'pending'
                    task['push_link'] = 'abcdef'
                else:
                    task['status'] = 'todo'

        all_rewards = []
        for rewards in available_rewards.values():
            all_rewards.extend(rewards)

        return {
            'rewards': all_rewards
        }
            #[
            #     {
            #     'id': 'fasdadg',
            #     'amount': 0.01,
            #     'coin': 'POPE',
            #     'text': 'Todo: Subscribe',
            #     'status': 'todo',
            #     'type': 'youtube-subscribe',
            #     'channel': 'UC7Rtksgq4z0c9uqqz2JDWNQ',
            # }, {
            #     'id': 'asGEW',
            #     'amount': 0.02,
            #     'coin': 'POPE',
            #     'text': 'Pending: Like',
            #     'status': 'pending',
            #     'type': 'youtube-like',
            #     'video': 'iWHRfPuJPnc',
            #     'push_link': '2SwMph'
            # }, {
            #     'id': 'XZBE00',
            #     'amount': 0.03,
            #     'coin': 'POPE',
            #     'text': 'Done: Comment',
            #     'status': 'done',
            #     'type': 'youtube-comment',
            #     'video': 'iWHRfPuJPnc',
            # }
            #]
