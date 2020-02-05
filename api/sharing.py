from flask import Blueprint

bp_sharing = Blueprint('sharing', __name__, url_prefix='/api/sharing')

# post /email/import/sheets
# получить ссылку на гугл таблицу, провалидировать
# вернуть:
#  - id для получения списка и проверки оплаты
#  - minter адрес и deeplink для оплаты
#  - в случае ошибки - адекватный меседж


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

