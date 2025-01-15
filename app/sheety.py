import pandas as pd
from app import app
import requests

username = app.config['SHEETY_USERNAME']
bearer_token = app.config['SHEETY_BEARER']

def fetch_sheet_data(spreadsheet_name, sheet_name) -> pd.DataFrame:
    """
    Fetch from the Sheety API the info necessary to generate price tags pdf.
    """
    url = f"https://api.sheety.co/{username}/{spreadsheet_name}/{sheet_name}"
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return pd.DataFrame(response.json().get('etiquetas', []))
