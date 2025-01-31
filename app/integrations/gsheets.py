import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def connect_to_gsheet(spreadsheet_id, sheet_name, credentials_path) -> gspread.worksheet.Worksheet: 
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    ss = client.open_by_key(spreadsheet_id)
    return ss.worksheet(sheet_name)

def get_sheet_data(spreadsheet_id, sheet_name, credentials_path, include_row_num=False) -> list[dict]:
    """Returns listt of dicts where keys are column headers (first row)."""
    sheet = connect_to_gsheet(spreadsheet_id, sheet_name, credentials_path)
    data = sheet.get_all_records()

    if include_row_num:
        for i, row in enumerate(data, start=1):  # Start row numbers at 1
            row["Row Number"] = str(i)

    return data 

def get_sheet_as_dataframe(spreadsheet_id, sheet_name, credentials_path, include_row_num=False) -> pd.DataFrame:
    data = get_sheet_data(spreadsheet_id, sheet_name, credentials_path, include_row_num)
    return pd.DataFrame(data)
