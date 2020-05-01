import logging
from http import HTTPStatus

import requests
from urllib.parse import parse_qs, urlparse

from cachetools.func import ttl_cache
from flask import Blueprint
from flask_restx import Api, Resource, reqparse, fields
from flask_uploads import extension
from mintersdk.sdk.wallet import MinterWallet
from mintersdk.shortcuts import to_pip, to_bip
from werkzeug.datastructures import FileStorage

from api.logic.core import generate_and_save_wallet
from api.models import RewardCampaign, RewardIcon
from api.upload import images
from config import YOUTUBE_APIKEY, YYY_PUSH_URL
from helpers.misc import uuid
from minter.helpers import TxDeeplink, find_gas_coin
from minter.tx import estimate_custom_fee, send_coin_tx
from providers.minter import get_first_transaction
from providers.nodeapi import NodeAPI

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
        one_tx_fee = float(estimate_custom_fee(coin) or 0)
        campaign_cost = (action_reward + one_tx_fee) * count
        deeplink = TxDeeplink.create('send', to=wallet['address'], value=campaign_cost, coin=coin)

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

    def delete(self, campaign_id):
        campaign = RewardCampaign.get_or_none(link_id=campaign_id, status='open')
        if not campaign:
            return {}, HTTPStatus.NOT_FOUND

        response = NodeAPI.get_balance(campaign.address)
        balances = response['balance']
        campaign_balance = to_bip(balances.get(campaign.coin, '0'))
        if campaign_balance:
            tx_fee = estimate_custom_fee(campaign.coin)
            gas_coin = find_gas_coin(balances) if tx_fee is None else campaign.coin
            if not gas_coin:
                return {
                    'error': f'Campaign coin not spendable.'
                             f'Send any coin to campaign address {campaign.address} to pay fee'
                }, HTTPStatus.BAD_REQUEST
            private_key = MinterWallet.create(mnemonic=campaign.mnemonic)['private_key']
            refund_address = get_first_transaction(campaign.address)
            nonce = int(response['transaction_count']) + 1

            tx_fee = 0 if tx_fee is None else tx_fee
            tx = send_coin_tx(
                private_key, campaign.coin, campaign_balance - tx_fee, refund_address,
                nonce, gas_coin=campaign.coin)
            NodeAPI.send_tx(tx, wait=True)

        campaign.status = 'closed'
        campaign.save()
        return {'success': True}

    def get(self, campaign_id):
        campaign = RewardCampaign.get_or_none(link_id=campaign_id, status='open')
        if not campaign:
            return {}
        balances = NodeAPI.get_balance(campaign.address)['balance']
        campaign_balance = to_bip(balances.get(campaign.coin, '0'))
        # if not campaign_balance:
        #     return {}
        times_completed = campaign.times_completed
        reward = float(to_bip(campaign.action_reward))
        value_spent = times_completed * reward
        return {
            'id': campaign.link_id,
            'name': campaign.name,
            'address': campaign.address,
            'count': campaign.count,
            'coin': campaign.coin,
            'balance': float(campaign_balance),
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
            action_type__in=['youtube-like', 'youtube-comment', 'youtube-subscribe', 'youtube-watch'], status='open'):

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
        return {}
    campaigns = get_campaigns_by_video_id(video_id)
    campaigns_ = {}
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
                    casted_duration = float(cmp.action_params['duration'].replace(',', '.'))
                except Exception:
                    continue
                params['duration'] = casted_duration

            rewards[action_type].append({
                'id': cmp.link_id,
                'amount': cmp.action_params['reward'],
                'coin': cmp.coin,
                'text': cmp.name,
                'type': cmp.action_type,
                'icon': cmp.icon.url if cmp.icon else None,
                'status': 'todo',
                **params
            })
            campaigns_[cmp.link_id] = cmp
    return rewards, campaigns_


def generate_push(campaign):
    response = NodeAPI.get_balance(campaign.address)
    balances = response['balance']
    campaign_balance = to_bip(balances.get(campaign.coin, '0'))
    if not campaign_balance:
        logging.info(f'Campaign {campaign.link_id} {campaign.name}: balance too low {campaign_balance}')
        return

    tx_fee = estimate_custom_fee(campaign.coin)
    reward = to_bip(campaign.action_reward)

    if campaign_balance < reward + tx_fee:
        logging.info(f'Campaign {campaign.link_id} {campaign.name}: balance too low {campaign_balance}')
        return

    push = generate_and_save_wallet()
    private_key = MinterWallet.create(mnemonic=campaign.mnemonic)['private_key']
    nonce = int(response['transaction_count']) + 1

    tx = send_coin_tx(
        private_key, campaign.coin, reward + tx_fee, push.address,
        nonce, gas_coin=campaign.coin)
    NodeAPI.send_tx(tx, wait=True)
    logging.info(f'Campaign {campaign.link_id} {campaign.name} rewarded {reward} {campaign.coin}, fee {tx_fee}')

    campaign.times_completed += 1
    if campaign.times_completed == campaign.count:
        campaign.status = 'close'
        logging.info(f'Campaign {campaign.link_id} {campaign.name} finished!')
    campaign.save()
    return YYY_PUSH_URL + push.link_id


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
        campaigns = {}
        if args['video']:
            video_id = parse_video_id(args['video'])
            available_rewards, campaigns = get_available_rewards_video(video_id)

        if args['type'] == 'youtube-watch' and 'youtube-watch' in available_rewards:
            duration = args['duration'] or 0
            for task in available_rewards['youtube-watch']:
                if duration >= task['duration']:
                    push_link = generate_push(campaigns[task['id']])
                    if not push_link:
                        task['status'] = 'errored'
                        continue
                    task['status'] = 'done'
                    task['push_link'] = push_link

        if args['type'] in ['youtube-comment', 'youtube-like', 'youtube-subscribe']:
            for task in available_rewards.get(args['type'], []):
                push_link = generate_push(campaigns[task['id']])
                if not push_link:
                    task['status'] = 'errored'
                    continue
                task['status'] = 'done'
                task['push_link'] = push_link

        all_rewards = []
        for rewards in available_rewards.values():
            all_rewards.extend([r for r in rewards if r['status'] != 'errored'])
        logging.info(all_rewards)
        return {
            'rewards': all_rewards
        }
