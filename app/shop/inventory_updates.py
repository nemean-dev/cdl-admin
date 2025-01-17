import os
import json
from typing import Optional
from datetime import datetime, timezone
import pandas as pd
from numpy import nan
from app.shop.shopify import get_variants_by_sku

base_path = os.path.join(os.getcwd(), 'data/update_quantities')
quantities_file_path = os.path.join(base_path, 'quantities.csv')
timestamp_file_path = os.path.join(base_path, 'timestamp')

def get_local_inventory() -> tuple[pd.DataFrame, str, int]:
    """
    Returns a tuple with: 
    - the records stored in 'data/update_quantities/quantities.csv'
    - the time represented by the timestamp stored in 'data/update_quantities/timestamp'
    - the number of errors
    
    Both are None if files missing.
    """
    try:
        data = pd.read_csv(quantities_file_path)
        with open(timestamp_file_path, 'r') as f:
            saved_time = float(f.read(50))
            time = datetime.fromtimestamp(saved_time, tz=timezone.utc)
        total_errors = data.loc[data['errors'] != 'none', 'errors'].count()
        
    except FileNotFoundError:
        data = None
        time = None
        total_errors = 0

    return data, time, total_errors

def delete_local_inventory():
    if os.path.exists(quantities_file_path):
        os.remove(quantities_file_path)
    if os.path.exists(timestamp_file_path):
        os.remove(timestamp_file_path)

def write_local_inventory(df: pd.DataFrame):
    df.to_csv(quantities_file_path)
    with open(timestamp_file_path, 'w') as f:
        now = datetime.now(timezone.utc)
        f.write(str(now.timestamp()))

def complete_sheety_data(sheety_df: pd.DataFrame) -> pd.DataFrame:
    # csv cols: sku, qty, display_name, vendor, new_price, price_delta, new_cost, cost_delta
    combined_data = []
    for index, row in sheety_df.iterrows():
        sku = row['clave (sku)']
        if not sku or sku != sku: continue
        new_price = row['nuevoPrecioVenta']
        new_cost = row['nuevoPrecioCompra']

        # Query shopify for the variant corresponding to this SKU
        variants = get_variants_by_sku(sku)

        if len(variants) >= 2:
            combined_data.append({
                'sku': sku,
                'errors': f'Hay más de un producto con clave "{sku}".'
            })
            continue
        elif len(variants) == 0:
            combined_data.append({
                'sku': sku,
                'errors': f'No se encontró ningún producto con clave "{sku}".'
            })
            continue
        elif new_price and not (isinstance(new_price, (int, float)) and 
                                (0 < new_price <= 7000 or new_price != new_price)): # x != x is true if x is nan!
            combined_data.append({
                'sku': sku,
                'errors': f'No es válido el precio de venta ingresado en este renglón (renglón {index + 2}).',
            })
            continue
        elif new_cost and not (isinstance(new_cost, (int, float)) and 
                                (0 < new_cost <= 20000 or new_cost != new_cost)):
            combined_data.append({
                'sku': sku,
                'errors': f'No es válido el precio de compra ingresado en el renglón {index + 2}.'
            })
            continue
        
        variant = variants[0]
        
        # row is from Google Sheets and variant is the corresponding Shopify productVariant
        combined_product_data = {
            'sku': sku, 
            'quantity': int(row['cantidadAAgregar']), 
            'displayName': variant['displayName'],
            'vendor': variant['vendor'],
            'newPrice': new_price if new_price else nan,
            'priceDelta': new_price - float(variant['price']) if new_price else nan,
            'newCost': new_cost if new_cost else nan,
            'costDelta': new_cost - float(variant['unitCost']) if new_cost else nan,
            'errors': 'none',
            'variantId': variant['variantId'],
            'productId': variant['productId'],
            'inventoryItemId': variant['inventoryItemId'],
        }
        combined_data.append(combined_product_data)
    
    # write combined data to csv for loading and add timestamp
    df = pd.DataFrame.from_records(combined_data)

    return df

def upload_product_quantities(df: pd.DataFrame):
    '''
    Uploads product quantities to shopify.
    
    Params:
    - df should contain the following columns: ,sku,quantity,displayName,vendor,newPrice,priceDelta,newCost,costDelta,errors
    '''

if __name__ == "__main__":
    data, time = get_local_inventory()
    print(time)
    print(data)