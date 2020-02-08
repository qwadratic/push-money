from api.models import PushCampaign, PushWallet
from jobs.scheduler import scheduler
from providers.mscan import MscanAPI
from providers.sendpulse import campaign_create

MAX_CAMPAIGNS_HOUR = 4


@scheduler.scheduled_job('interval', seconds=30)
def job_update_campaigns():
    to_check = PushCampaign \
        .select(PushCampaign, PushWallet) \
        .join(PushWallet, on=PushCampaign.wallet_link_id == PushWallet.link_id) \
        .where(PushCampaign.status == 'open')

    addr_cmp = {
        cmp.pushwallet.address: cmp for cmp in to_check
    }
    addresses = [cmp.pushwallet.address for cmp in to_check]
    address_info = MscanAPI.get_addresses(addresses)
    addr_pip_balance = {d['address']: int(d['balance']['BIP']) for d in address_info}
    to_start = [
        cmp for address, cmp in addr_cmp.items()
        if addr_pip_balance[address] >= int(cmp.cost_pip)
    ]
    for cmp in to_start:
        cmp.status = 'paid'
        cmp.save()
        scheduler.add_job(job_create_sendpulse_campaign, 'date', args=(cmp.id, ))


def job_create_sendpulse_campaign(cmp_id):
    cmp = PushCampaign.get(cmp_id)
    if cmp.status == 'paid':
        cmp.status = 'progress'

    book_id = cmp.sendpulse_addressbook_id
    campaign_id = campaign_create(book_id, test=[
        'ivak_@mail.ru', 'callmyduck@gmail.com'])
    cmp.sendpulse_campaign_id = campaign_id
    cmp.save()
