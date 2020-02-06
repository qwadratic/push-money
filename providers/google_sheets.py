import gspread
from gspread import NoValidUrlKeyFound
from gspread.exceptions import APIError
from oauth2client.service_account import ServiceAccountCredentials

from config import GOOGLE_CLIENT_KEY_FILENAME
from helpers.validation import is_email, to_number


def get_gspread_client():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CLIENT_KEY_FILENAME, scope)
    return gspread.authorize(credentials)


def get_spreadsheet(url):
    gc = get_gspread_client()
    try:
        spreadsheet = gc.open_by_url(url)
        spreadsheet.fetch_sheet_metadata()
        return spreadsheet
    except NoValidUrlKeyFound:
        return {'error': 'Spreadsheet URL invalid'}
    except APIError:
        return {'error': 'Make sure your spreadsheet is accessible by link and try again'}


def parse_recipients(spreadsheet):
    """ Spreadsheet should be 3 cols: email,name,amount """
    recipients = {}
    for worksheet in spreadsheet.worksheets():
        rows = worksheet.get_all_values()
        if not rows:
            continue
        if not len(rows[0]) == 3:
            continue
        for row in rows:
            email, name, amount = row
            amount = to_number(amount.strip())
            name = name.strip()

            if not is_email(email.strip()) or not amount:
                continue
            if email in recipients:
                continue
            recipients[email] = {'name': name, 'amount': amount}
    return recipients
