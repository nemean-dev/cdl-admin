import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from flask import current_app

def connect_to_gsheet(spreadsheet_id, sheet_name) -> gspread.worksheet.Worksheet: 
    creds = Credentials.from_service_account_info(
        current_app.config.get('GSHEETS_CREDENTIALS'),
        scopes = ["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    ss = client.open_by_key(spreadsheet_id)
    
    return ss.worksheet(sheet_name)

def get_sheet_data(spreadsheet_id, sheet_name, include_row_num=False) -> list[dict]:
    """Returns listt of dicts where keys are column headers (first row)."""
    sheet = connect_to_gsheet(spreadsheet_id, sheet_name)
    data = sheet.get_all_records()

    if include_row_num:
        for i, row in enumerate(data, start=1):  # Start row numbers at 1
            row["Row Number"] = str(i)

    return data 

def get_sheet_as_dataframe(spreadsheet_id, sheet_name, include_row_num=False) -> pd.DataFrame:
    data = get_sheet_data(spreadsheet_id, sheet_name, include_row_num)
    return pd.DataFrame(data)

def append_df_to_sheet(spreadsheet_id, sheet_name, df: pd.DataFrame) -> None:
    """
    Appends df rows to a worksheet.
    Missing columns are added to the first row if needed.
    """
    sheet = connect_to_gsheet(spreadsheet_id, sheet_name)
    existing_data = sheet.get_all_values()
    
    if existing_data:
        existing_headers = existing_data[0]
    else:
        existing_headers = []
    
    df_columns = df.columns.tolist()
    
    # Ensure all columns exist in the sheet
    new_columns = [col for col in df_columns if col not in existing_headers]
    if new_columns:
        existing_headers.extend(new_columns)
        sheet.update('A1', [existing_headers])
    
    # reorder DataFrame columns to match the sheet's
    ordered_df = df.reindex(columns=existing_headers, fill_value="")

    next_row = len(existing_data) + 1
    
    # Ensure there are enough rows in the sheet
    current_row_count = len(existing_data)
    required_rows = len(ordered_df) + next_row - 1
    if required_rows > current_row_count:
        sheet.add_rows(required_rows - current_row_count)
    
    # Append from first empty row
    ordered_df = ordered_df.fillna("") # remove nan to avoid errors
    sheet.update(f'A{next_row}', ordered_df.values.tolist())

def clear_sheet_except_header(spreadsheet_id, sheet_name) -> None:
    """
    Clears all content in a worksheet except for the first row (headers).
    """
    sheet = connect_to_gsheet(spreadsheet_id, sheet_name)
    existing_data = sheet.get_all_values()
    
    if existing_data:
        headers = existing_data[0]
        sheet.clear()
        sheet.update('A1', [headers])
