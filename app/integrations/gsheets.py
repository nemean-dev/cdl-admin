import pandas as pd
from flask import current_app
import gspread
from google.oauth2.service_account import Credentials

CREDENTIALS = current_app.config['GSHEETS_CREDENTIALS']
CAPTURA_ID = current_app.config['GSHEETS_CAPTURA_ID']

def connect_to_gsheet(spreadsheet_id, sheet_name, credentials_path=CREDENTIALS) -> gspread.worksheet.Worksheet: 
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    ss = client.open_by_key(spreadsheet_id)
    return ss.worksheet(sheet_name)

def get_sheet_data(spreadsheet_id, sheet_name) -> list[dict]:
    """Returns listt of dicts where keys are column headers (first row)."""
    sheet = connect_to_gsheet(spreadsheet_id, sheet_name)
    data = sheet.get_all_records()
    return data 

def get_sheet_as_dataframe(spreadsheet_id, sheet_name) -> pd.DataFrame:
    data = get_sheet_data(spreadsheet_id, sheet_name)
    return pd.DataFrame(data)
