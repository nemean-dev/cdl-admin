import pandas as pd
import requests
from flask import current_app

def fetch_sheet_data(spreadsheet_name, sheet_name) -> pd.DataFrame:
    """
    Fetch from the Sheety API the info necessary to generate price tags pdf.
    """
    base_url = f"https://api.sheety.co/{current_app.config['SHEETY_USERNAME']}"
    headers = {
        "Authorization": f"Bearer {current_app.config['SHEETY_BEARER']}"
    } # TODO: these two variables should be outside this function, as they are 
      # also used in put_record. but when I do that the app breaks.
      # How to access config variables during initialization?

    url = base_url + f"/{spreadsheet_name}/{sheet_name}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return pd.DataFrame(response.json().get(sheet_name, [])) #TODO: make sure all columns are in the dataframe because if no values are entered for a column sheety does not return it (since no record contains the field)

def fetch_etiquetas():
    return fetch_sheet_data('etiquetas', 'etiquetas')

def fetch_inventory_updates():
    return fetch_sheet_data('actualizarCantidades', 'cantidades')

def put_record(spreadsheet_name:str, sheet_name:str, row:int, payload:dict) -> bool:
    """
    Returns True if response is 200
    """
    base_url = f"https://api.sheety.co/{current_app.config['SHEETY_USERNAME']}"
    headers = {
        "Authorization": f"Bearer {current_app.config['SHEETY_BEARER']}"
    }
    url = base_url + f"/{spreadsheet_name}/{sheet_name}/{row}"
    res = requests.put(url, headers=headers, json=payload)
    return res.status_code == 200

def clear_inventory_updates_sheet():
    payload = {
        "script": {
            "deleteCantidades": "DELETE"
        }
    }
    return put_record('actualizarCantidades', 'scripts', 2, payload)