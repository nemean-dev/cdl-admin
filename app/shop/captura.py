from datetime import datetime, timedelta
import pandas as pd
from flask import current_app
import sqlalchemy as sa
from app import db
from app.models import Vendor
from app.utils import simple_lower_ascii, extra_strip, validate_spanish_characters, remove_whitespace, get_datestring
from app.shop.inventory import sku_available
from app.integrations.gsheets import get_sheet_as_dataframe

def get_captura() -> pd.DataFrame:
    '''Returns Captura worksheet with standardized column names'''
    # Get with gsheets connector
    captura_id = current_app.config['GSHEETS_CAPTURA_ID']
    creds = current_app.config['GSHEETS_CREDENTIALS']
    df = get_sheet_as_dataframe(captura_id, 'Captura', creds, include_row_num=True)

    # rename cols
    df.rename(inplace=True, columns=
        {
            'Proveedor': 'vendor',
            'Título': 'title',
            'Clave': 'sku',
            'Costo por unidad': 'cost',
            'Precio Venta': 'price',
            'Fecha Compra': 'dateOfPurchase',
            'Cantidad': 'quantityDelta', #TODO: add who tagged the products. Can be managed in the app
            'Row Number': 'rowNum'
        })
    
    return df

def captura_clenup_and_validation(captura: pd.DataFrame) -> pd.DataFrame:
    '''
    Returns a cleaned up version of the dataframe with an additional columns 'errors' 
    and 'warnings':
    - 'errors': list of error messages for this product
    - 'warnings': list of warning messages for this product

    If both lists are empty, it means the evaluation was successful for that product.
    '''
    df = captura.copy()

    df['info'] = pd.NA
    df['warnings'] = pd.NA
    df['errors'] = pd.NA

    df = validate_vendors(df)
    df = validate_title(df)
    df = validate_skus(df)
    df = validate_price_and_cost(df)
    df = validate_fecha_compra(df)
    df = validate_quantity(df)

    return df

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

def add_info(df: pd.DataFrame, row_filter, message: str) -> None:
    """Appends an info message to the 'info' column for rows matching row_filter."""
    df.loc[row_filter, 'info'] = df.loc[row_filter, 'info'].apply(
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
                add_info(df, row_filter, f"Artesano remombrado de '{vendor_name}' a '{vendor_in_db.name}'")

        else:
            # Add an error if no matching vendor was found in the database
            add_error(df, df['vendor'] == vendor_name, f"El artesano '{vendor_name}' no existe en la base de datos. Si es un proveedor nuevo, <a href=\"#\">agrégalo</a>.")

    return df

def validate_title(df) -> pd.DataFrame:
    '''
    Validates the 'title' column in the dataframe.
    - Adds an error if the value is not a string.
    - Adds a warning if the title contains invalid Spanish characters.
    - Strips multiple whitespace characters.
    '''
    for index, row in df.iterrows():
        title = row['title']
        
        if not isinstance(title, str):
            add_error(df, df.index == index, "El título debe ser un texto válido.") #TODO: boolean mask really is unnecessary in various add_error and add_warning calls. Might slow execution
            continue
        
        df.at[index, 'title'] = extra_strip(title)
        
        if not validate_spanish_characters(title):
            add_warning(df, df.index == index, "El título contiene caracteres no válidos en español.")
    
    return df

def validate_skus(df) -> pd.DataFrame:
    '''
    Validates the 'sku' column in the dataframe.
    - Adds an error if the value is not a string.
    - Removes all spaces/blank characters using remove_whitespace.
    - Verifies that the SKU is valid using sku_available(sku). #TODO
    '''
    for index, row in df.iterrows():
        sku = row['sku']
        
        if not isinstance(sku, str):
            add_error(df, df.index == index, "El SKU debe ser texto.")
            continue
        
        cleaned_sku = remove_whitespace(sku)
        df.at[index, 'sku'] = cleaned_sku
        
        if not sku_available(cleaned_sku):
            add_error(df, df.index == index, "El SKU no es válido o ya está en uso.")
    
    return df

def validate_price_and_cost(df) -> pd.DataFrame:
    '''
    - Makes sure all price values are numerical and positive, adds warning if 
    price >20,000 or <10. Cannot be empty.
    - Makes sure all cost values are numerical or empty.
    - check that cost * LOWER_BOUND_MULTIPLIER <= price <= cost * UPPER_BOUND_MULTIPLIER. 
    If it is not in the range, adds warning with add_warning 
    '''
    LOWER_BOUND_MULTIPLIER = 1.5
    UPPER_BOUND_MULTIPLIER = 5

    for index, row in df.iterrows():
        price = row['price']
        cost = row['cost']
        
        if not isinstance(price, (int, float)) or price <= 0:
            add_error(df, df.index == index, "El precio debe ser un número positivo.")
            continue
        
        if not (isinstance(cost, (int, float)) and cost >= 0) and pd.notna(cost):
            add_error(df, df.index == index, "El costo debe ser un número positivo o vacío.")
            continue
        
        if pd.notna(cost):
            if not (cost * LOWER_BOUND_MULTIPLIER <= price <= cost * UPPER_BOUND_MULTIPLIER):
                add_warning(df, df.index == index, "El precio no está dentro del rango permitido respecto al costo.")
        
        if price > 20000:
            add_warning(df, df.index == index, "El precio es demasiado alto.")
        elif price < 10:
            add_warning(df, df.index == index, "El precio es demasiado bajo.")
    
    return df

def validate_fecha_compra(df) -> pd.DataFrame:
    '''
    - makes sure values are empty or a date.
    - If a date/number, checks that the date is from past 2 months and 
    substitutes it for string in format yyyy-mm-dd. If not in last 2 months add_warning
    - If empty, it substitutes for 1st of current month yyyy-mm-01
    '''
    today = datetime.today()
    two_months_ago = today - timedelta(days=60)

    for index, row in df.iterrows():
        fecha_compra = row['dateOfPurchase']
        
        # if empty use 1st of month
        if pd.isna(fecha_compra):
            df.at[index, 'dateOfPurchase'] = get_datestring(today.replace(day=1))
            continue
        
        try:
            fecha_compra = pd.to_datetime(fecha_compra) # TODO: find a way to  verify that google sheets is sending the day/month/year. Because it depends on the 'locale' settings in the worksheet and sometimes the worksheet defaults to US locale where month goes first.
        except Exception:
            add_error(df, df.index == index, "fecha inválida")
            continue
        
        if pd.notna(fecha_compra):
            if fecha_compra < two_months_ago:
                add_warning(df, df.index == index, "La fecha debe ser de los últimos 6 meses")

            df.at[index, 'dateOfPurchase'] = fecha_compra.strftime('%Y-%m-%d')
    
    return df

def validate_quantity(df) -> pd.DataFrame:
    '''
    - Values must be positive integers. they can be float so long as the decimal value is 0.
    - add_warning if value > 100
    '''
    for index, row in df.iterrows():
        quantity = row['quantityDelta']
        
        if not isinstance(quantity, (int, float)) or quantity <= 0 or quantity % 1 != 0:
            add_error(df, df.index == index, "La cantidad no es válida")
            continue
        
        if quantity > 100:
            add_warning(df, df.index == index, "La cantidad es bastante alta. Es correcta?")
    
    return df

