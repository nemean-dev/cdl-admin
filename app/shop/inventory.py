import os
import re
import json
from typing import Union
from datetime import datetime, timezone, timedelta
import pandas as pd
from numpy import nan
from flask import current_app
from app import storage_service
from app.integrations.storage import StorageNotFoundError
import app.shop.graphql_queries as q
from app.integrations.shopify import graphql_query, raise_for_user_errors

quantities_path = 'quantities/quantities.csv'
timestamp_path  = 'quantities/timestamp'

def get_local_inventory() -> tuple[pd.DataFrame, str, int]:
    """
    Returns a tuple with: 
    - the records stored in '<data_dir>update_quantities/quantities.csv'
    - the time represented by the timestamp stored in '<data_dir>/update_quantities/timestamp'
    - the number of errors
    
    Both are None if files missing.
    """
    storage = storage_service()
    try:
        data = storage.download_csv(quantities_path)
        saved_time = float(storage.download_text(timestamp_path))
        time = datetime.fromtimestamp(saved_time, tz=timezone.utc)
        total_errors = data.loc[data['errors'] != 'none', 'errors'].count()
        
    except StorageNotFoundError:
        data = None
        time = None
        total_errors = 0

    return data, time, total_errors

def delete_local_inventory():
    storage = storage_service()
    storage.delete(quantities_path)
    storage.delete(timestamp_path)

def write_local_inventory(df: pd.DataFrame):
    storage = storage_service()
    storage.upload_csv(quantities_path, df)
    now = datetime.now(timezone.utc)
    storage.upload_text(timestamp_path, str(now.timestamp()))

def complete_sheety_data(sheety_df: pd.DataFrame) -> pd.DataFrame:
    # csv cols: sku, qty, display_name, vendor, new_price, price_delta, new_cost, cost_delta
    combined_data = []
    for index, row in sheety_df.iterrows():
        sku = row.get('clave (sku)',            nan)
        if not sku or sku != sku: continue
        new_price = row.get('nuevoPrecioVenta', nan) # TODO: remove these 4 `nan` and instead make sure the sheety module returns all columns
        new_cost = row.get('nuevoPrecioCompra', nan)
        qty = row.get('cantidadAAgregar', nan)
        if qty == qty:
            qty = int(qty)
        fecha_de_compra = row.get('fechaDeCompra (yyyyMmDd)', nan)
        if fecha_de_compra != fecha_de_compra: #if fecha de compra is nan
            fecha_de_compra = datetime.now(timezone(timedelta(hours=-6))).strftime('%Y-%m-%d') #TODO: make env variable for the store's local timezone and use throughout app. Also in db.

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

        new_cost_history_value = variant['costHistoryValue']
        new_cost_history_value.append({
            "costo": new_cost,
            "cantidad": qty,
            "fecha de compra": fecha_de_compra,
        })
        new_cost_history = {
            "key": "cost_history",
            "namespace": "custom",
            "ownerId": variant['variantId'],
            "type": "json",
            "compareDigest": variant['costHistoryCompareDigest'],
            "value": new_cost_history_value
        }

        joined_product_data = {
            'sku': sku, 
            'quantity': qty, 
            'displayName': variant['displayName'],
            'vendor': variant['vendor'],
            'newPrice': new_price,
            'priceDelta': new_price - float(variant['price']),
            'newCost': new_cost,
            'costDelta': new_cost - float(variant['unitCost']),
            'errors': 'none',
            'variantId': variant['variantId'],
            'productId': variant['productId'],
            'inventoryItemId': variant['inventoryItemId'],
            'costHistory': json.dumps(new_cost_history),
        }
        combined_data.append(joined_product_data)
    
    df = pd.DataFrame.from_records(combined_data)

    return df

def get_variants_by_sku(sku:str) -> list[dict]:
    """
    Get info on product variants that match the given SKU.

    Returns a list of variants that have the given SKU.
    E.g. [
      {
        "sku": "abc", # the given sku
        "variantId": "gid://shopify/ProductVariant/1234567890",
        "displayName": "Ceramic Vase - Default Title",
        "vendor": "John Doe",
        "price": 670,
        "unitCost": 400,
        "inventoryItemId": "gid://shopify/...",
      }
    ]
    """
    query = q.get_variants_by_sku % sku

    res = graphql_query(query)
    data = res.json()['data']

    variants = []
    for variant in data['productVariants']['nodes']:
        unit_cost = variant['inventoryItem']['unitCost']
        unit_cost = unit_cost['amount'] if unit_cost else nan
        variant_data = {
            "sku": sku,
            "variantId": variant['id'],
            "displayName": variant['displayName'],
            "vendor": variant['product']['vendor'],
            "price": variant['price'],
            "unitCost": unit_cost,
            "inventoryItemId": variant['inventoryItem']['id'],
            "productId": variant['product']['id'],
            "costHistoryValue": variant['metafield']['jsonValue'] if variant['metafield'] else [],
            "costHistoryCompareDigest": variant['metafield']['compareDigest'] if variant['metafield'] else []
        }
        variants.append(variant_data)

    return variants

def set_variant_cost(inventory_item_id:str, cost:float) -> None:
    """
    Sets the unitCost for a product variant.

    Params:
    - inventory_item_id: the id of the inventory item corresponding to the 
    product variant we wish to update
    - cost: in the store's default currency.
    """
    query = q.set_variant_cost
    variables = {
        "id": inventory_item_id,
        "input": {
            "cost": cost
        }
    }
    res = graphql_query(query, variables)
    raise_for_user_errors(res, 'inventoryItemUpdate')

def set_variant_price(product_id:str, variant_id:Union[str, list[str]], price:Union[float, list[float]]) -> None:
    """
    Sets the price for a product variant, or for multiple product variants if 
    they all belong to the same product.

    Params:
    - product_id
    - variant_id: a single id string or a list of IDs. In any case, the variants
    must belong to the product associated wth the product_id.
    - price: a single price or a list of prices of the same length as variant_id
    """
    if isinstance(variant_id, list):
        if not isinstance(price, list) or len(price) != len(variant_id):
            raise ValueError(
                "If 'variant_id' is a list, then 'price' must be a list of the same length.")
        
    else:
        if not isinstance(price, (int, float)):
            raise ValueError("If only one variant id was entered, price must be a single numerical value.")
        
        variant_id, price = [variant_id], [price]
    
    variants = []
    for i in range(len(variant_id)):
        variants.append({
            "id": variant_id[i],
            "price": price[i]
        })

    query = q.set_variant_price
    variables = {
        "productId": product_id,
        "variants": variants
    }
    res = graphql_query(query, variables)
    raise_for_user_errors(res, 'productVariantsBulkUpdate')

def adjust_variant_quantities(changes: list[dict], reason: str = 'received', name: str = 'available') -> None:
    """
    Adjust 'available' quainties for product variants.

    Params:
    - changes: a list of changes. Each change is a dict with 'inventoryItemId' 
    and 'delta' (how many items to add/subract) keys. (Note: delta can be 
    negative, in which case items will be subtracted. If so, change 'reson' to 
    something other than 'received'; see Shopify docs for other options
    - reason: the reason for the changes. 
    See possible values: https://shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states#set-inventory-quantities-on-hand
    - name: also see docs for possible names
    
    Example:
    e.g. changes = [
        {
            "inventoryItemId": "gid://shopify/InventoryItem/1234567890"
            "delta": 20
        },
        {
            "inventoryItemId": "gid://shopify/InventoryItem/0987654321"
            "delta": 33
        },
    ]
    adjust_variant_quantities(changes=changes)
    """
    # TODO: perhaps make the referenceDocumentUri the URI of the AdminAction that made this change.
    # see: https://shopify.dev/docs/api/admin-graphql/2025-01/mutations/inventoryAdjustQuantities
    
    LOCATION_ID = current_app.config['SHOPIFY_LOCATION_ID']
    changes_with_id = [
        {**change, "locationId": LOCATION_ID} for change in changes
    ]
    query = q.adjust_variant_quantities
    variables = {
        "input": {
            "reason": reason,
            "name": name,
            "changes": changes_with_id
        }
    }
    res = graphql_query(query, variables)
    raise_for_user_errors(res, 'inventoryAdjustQuantities')
    current_app.logger.info(f"Inventory adjusted for {len(changes)} variants. Response: {res.text}")

def set_metafields(metafields=list[dict]) -> str:
    '''
    Each metafield in the list should have the following format.
    {
      "key": "some_key",
      "namespace": "the_namespace",
      "ownerId": "e.g. the variant ID or the product ID",
      "type": 'e.g. "json"',
      "compareDigest": "abc123456",
      "value": "value to set"
    }
    For supported types see: https://shopify.dev/docs/apps/build/custom-data/metafields/list-of-data-types

    Returns error message to show user if there is an error.
    '''
    for metafield in metafields:
        metafield['value'] = json.dumps(metafield['value'])
    query = q.set_metafields
    for i in range(0, len(metafields), 25): # we can only upload 25 metafields at a time
        batch = metafields[i:i+25]
        variables = {
            "metafields": batch
        }
        try:
            res = graphql_query(query, variables)
            raise_for_user_errors(res, queried_field='metafieldsSet')
        except:
            current_app.logger.error(f"Errors encountered while uploading {len(batch)} metafields. Problem batch is from metafield #{i+1} to #{i+len(batch)}.")
            raise
        else:
            current_app.logger.info(f'{len(batch)} metafields updated in batch #{i/25 + 1}.')

def get_variants_using_query(query: str, cursor: str=None) -> tuple[list[dict], str]:
    """Get useful information on the variants and their respective product.

    Returns (products, cursor) duple.
    - products: list[dict]
    - endCursor: str | None
      - endCursor is None if there is no next page.
    
    Params
    - query: will be used as the 'query' variable in the graphql query below:

    Query:
    ```
    query GetProductVariants ($query: String!) {
      productVariants(first: 3, query:$query) {
        nodes {
          # some fields
        }
      }
    }
    ```
    """
    query = q.get_variants_from_products_query % query
    # variables = {
    #     "query": f'"{query}"'
    # } TODO: why does this not work?
    try:
        res = graphql_query(query)
        print(json.dumps(res.text))
    except Exception as e:
        current_app.logger.warning(f"Errors encountered while retrieving queried products.\n  query: {query}\n  Error: {e}")
        raise
    
    page_info = res.json()['data']['products']['pageInfo']
    if page_info['hasNextPage']:
        end_cursor = page_info['endCursor']
    else:
        end_cursor = None
    
    return res.json()['data']['products']['nodes'], end_cursor
    # TODO implement pagination

def valid_sku(sku: str) -> bool:
    valid_chars = '^[0-9a-zA-ZáéíóúÁÉÍÓÚñÑ_-]*$'
    return len(sku) < 16 and re.fullmatch(valid_chars, sku, re.UNICODE) is not None

def sku_available(sku: str) -> bool:
    '''True if sku is available and contains no special characters and is not too long.'''
    if not valid_sku(sku):
        return False
    
    query = q.get_variant_id_by_sku % sku

    res = graphql_query(query)
    data = res.json()['data']

    return len(data['productVariants']['nodes']) == 0


if __name__ == "__main__":
    data, time = get_local_inventory()
    print(time)
    print(data)
