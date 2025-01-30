import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def connect_to_gsheet(spreadsheet_id, sheet_name, credentials_path) -> gspread.worksheet.Worksheet: 
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    ss = client.open_by_key(spreadsheet_id)
    return ss.worksheet(sheet_name)

def get_sheet_data(spreadsheet_id, sheet_name, credentials_path) -> list[dict]:
    """Returns listt of dicts where keys are column headers (first row)."""
    sheet = connect_to_gsheet(spreadsheet_id, sheet_name, credentials_path)
    data = sheet.get_all_records()
    return data 

def get_sheet_as_dataframe(spreadsheet_id, sheet_name, credentials_path) -> pd.DataFrame:
    data = get_sheet_data(spreadsheet_id, sheet_name, credentials_path)
    return pd.DataFrame(data)
