import pandas as pd
from flask import current_app
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
    df = validate_vendors(df)
    df = validate_title(df)
    df = validate_skus(df)
    df = validate_price_cost(df)
    df = validate_fecha_compra(df)
    df = validate_quantity(df)

    return df.to_dict(orient='records')

def validate_vendors(df) -> pd.DataFrame:
    '''
    - Matches with vendor db regardless of capitalization, accentuation, or multiple 
    spaces and punctuation. Replaces with the actual name in the db.
    '''
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
