import pandas as pd
from flask import current_app
import sqlalchemy as sa
from app import db
from app.models import Vendor
from app.utils import simple_lower_ascii
from app.integrations.gsheets import get_sheet_as_dataframe

def get_captura() -> pd.DataFrame:
    '''Returns Captura worksheet with standardized column names'''
    # Get with gsheets connector
    captura_id = current_app.config['GSHEETS_CAPTURA_ID']
    creds = current_app.config['GSHEETS_CREDENTIALS']
    df = get_sheet_as_dataframe(captura_id, 'Captura', creds)

    # rename cols
    df.rename(inplace=True, columns=
        {
            'Proveedor': 'vendor',
            'Título': 'title',
            'Clave': 'sku',
            'Precio Compra': 'cost',
            'Precio Venta': 'price',
            'Fecha Compra': 'dateOfPurchase',
            'Cantidad': 'quantityDelta', #TODO: add who tagged the products. Can be managed in the app
        })
    
    return df

def captura_clenup_and_validation(captura: pd.DataFrame) -> list[dict]:
    '''
    Returns a cleaned up version of the dataframe with an additional columns 'errors' 
    and 'warnings':
    - 'errors': list of error messages for this product
    - 'warnings': list of warning messages for this product

    If both lists are empty, it means the evaluation was successful for that product.
    '''
    df = captura.copy()

    df['warnings'] = pd.NA
    df['errors'] = pd.NA

    df = validate_vendors(df)
    df = validate_title(df)
    df = validate_skus(df)
    df = validate_price_cost(df)
    df = validate_fecha_compra(df)
    df = validate_quantity(df)

    return df.to_dict(orient='records')

def add_warning(df: pd.DataFrame, row_filter, message: str) -> None:
    """Appends a warning message to the 'warnings' column for rows matching row_filter."""
    df.loc[row_filter, 'warnings'] = df.loc[row_filter, 'warnings'].apply(
        lambda x: f"{x}; {message}" if pd.notna(x) else message
    )

def add_error(df: pd.DataFrame, row_filter, message: str) -> None:
    """Appends an error message to the 'errors' column for rows matching row_filter."""
    df.loc[row_filter, 'errors'] = df.loc[row_filter, 'errors'].apply(
        lambda x: f"{x}; {message}" if pd.notna(x) else message
    )

def validate_vendors(df) -> pd.DataFrame:
    '''
    - Matches with vendor db regardless of capitalization, accentuation, or multiple 
    spaces and punctuation. Replaces with the actual name in the db.
    '''
    unique_vendors = df['vendor'].dropna().unique()

    for vendor_name in unique_vendors:
        # search for a corresponding vendor in db
        normalised_vendor_name = simple_lower_ascii(vendor_name)        
        vendor_in_db = db.session.scalar(sa.select(Vendor).where(Vendor.compare_name == normalised_vendor_name))

        # rows corresponding to current iteration
        row_filter = df['vendor'] == vendor_name

        if vendor_in_db:
            # if the entered name does not exactly match the db name
            if vendor_name != vendor_in_db.name:
                #update the df for the correct name
                df.loc[row_filter, 'vendor'] = vendor_in_db.name
                #add warning that row changed #TODO: keep this?
                add_warning(df, row_filter, f"Artesano remombrado de '{vendor_name}' a '{vendor_in_db.name}'")

        else:
            # Add an error if no matching vendor was found in the database
            add_error(df, df['vendor'] == vendor_name, f"El artesano '{vendor_name}' no existe en la base de datos. Si es un proveedor nuevo, <a href=\"#\">agrégalo</a>.")

    return df

def validate_title(df) -> pd.DataFrame:
    '''
    - string
    - Raises warning if title has an non-acute spanish accent.
    - strips and removes consecutive spaces.
    '''
    return df

def validate_skus(df) -> pd.DataFrame:
    '''
    - string
    - verifies that the skus are not in use by another product. Will mark as equal
    skus that only differ on capitalization.
    - makes sure no special characters were entered
    - removes all spaces/blank characters
    '''
    return df

def validate_price_cost(df) -> pd.DataFrame:
    '''
    - Makes sure all price values are numerical and positive, adds warning if too high or too low
    - Makes sure all cost values are numerical or empty.
    - If cost is given, makes sure price is in range (set in Config lower and upper bound multipliers)
    '''
    return df

def validate_fecha_compra(df) -> pd.DataFrame:
    '''
    - makes sure values are empty or a date.
    - If a date/number, checks that the date is from past 6 months and 
    substitutes it for string in format yyyy-mm-dd
    - If empty, it substitutes for 1st of current month yyyy-mm-01
    '''
    return df

def validate_quantity(df) -> pd.DataFrame:
    '''
    - Values must be positive integers
    - warning if value > 100
    '''
    return df
