from flask import Blueprint, request, jsonify
from gspread import Spreadsheet

from api.consts import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from api.logic.core import generate_and_save_wallet
from api.models import PushCampaign
from minter.helpers import create_deeplink
from providers.google_sheets import get_spreadsheet, parse_recipients
from providers.sendpulse import prepare_campaign

bp_sharing = Blueprint('sharing', __name__, url_prefix='/api/sharing')

# post /email/import
# получить ссылку на гугл таблицу, провалидировать
# вернуть:
#  - id для получения списка и проверки оплаты
#  - minter адрес и deeplink для оплаты
#  - в случае ошибки - адекватный меседж


@bp_sharing.route('/email-import', methods=['POST'])
def email_import():
    payload = request.get_json() or {}
    spreadsheet_url = payload.get('google_sheet_url')
    if not spreadsheet_url:
        return jsonify({'error': 'Sheet url not specified'}), HTTP_400_BAD_REQUEST

    spreadsheet_or_error = get_spreadsheet(spreadsheet_url)

    if isinstance(spreadsheet_or_error, dict):
        return jsonify(spreadsheet_or_error), HTTP_400_BAD_REQUEST
    elif not isinstance(spreadsheet_or_error, Spreadsheet):
        return jsonify({'error': 'Internal API error'}), HTTP_500_INTERNAL_SERVER_ERROR

    recipients = parse_recipients(spreadsheet_or_error)
    if not recipients:
        return jsonify({'error': 'Recipient list is empty'}), HTTP_400_BAD_REQUEST

    campaign_wallet = generate_and_save_wallet(None, None, None)
    campaign = PushCampaign.create(wallet_link_id=campaign_wallet.link_id)
    for info in recipients.values():
        wallet = generate_and_save_wallet(None, None, None)
        info['token'] = wallet.link_id
    campaign_info = prepare_campaign(f'dev_{campaign.wallet_link_id}', recipients)
    campaign.sendpulse_addressbook_id = campaign_info['addressbook_id']
    campaign.save()

    total_cost = sum(info['amount'] for info in recipients.values())
    total_fee = 0.01 * len(recipients)
    return jsonify({
        'id': campaign.id,
        'address': campaign_wallet.address,
        'deeplink': create_deeplink(campaign_wallet.address, total_cost + total_fee)
    })


# get /<id>
# вернуть получателей рассылки, тип рассылки (только email) и количество монет

# get /<id>/check-payment
# проверить оплачена ли рассылка
#  - если нет, вернуть статус неок, сумму для оплаты и диплинк
#  - если да - статус ок

# get /<id>/stats
# статистика по рассылке


# рассылочная джоба:
#   - проверяет оплату неоплаченных рассылок
#   - генерит линки на шаринг (чеками?)
#   - рассылает емейлы


# джоба статистики:
#   - по оплаченным рассылкам обновляет стату открываний/доставки писем
