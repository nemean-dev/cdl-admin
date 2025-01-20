from typing import Union
import json
from time import sleep
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from numpy import nan
from flask import current_app
import app.shop.graphql_queries as q

# TODO same issue as in sheety module
# STORE = current_app.config['SHOPIFY_STORE']
# API_TOKEN = current_app.config['SHOPIFY_API_TOKEN']
# LOCATION_ID = current_app.config['SHOPIFY_LOCATION_ID']

class ShopifyQueryError(Exception):
    """
    Custom exception for Shopify GraphQL queries where the query syntax was incorrect.
    Usually response.json() will contain field 'errors'.
    """
    pass
class ShopifyUserError(Exception):
    """
    Custom exception for errors in Shopify GraphQL mutations where 'userErrors'
    list exists and is not empty.
    """
    pass
    
def graphql_query(query: str, variables: dict = None) -> requests.Response:
    """
    To query the Shopify GraphQL API. Use with both queries and mutations.

    Raises any errors (inlcuding 'errors' field in status code 200 responses)

    If doing mutations: 
    this function checks for errors BUT NOT for 'userErrors' in Shopify GraphQL 
    mutations. For that you can use raise_for_user_errors() instead.
    """
    STORE = current_app.config['SHOPIFY_STORE']
    API_TOKEN = current_app.config['SHOPIFY_API_TOKEN']
    url = f"https://{STORE}.myshopify.com/admin/api/2025-01/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": API_TOKEN,
    }

    if variables:
        payload = {
            'query': query,
            'variables': variables
        }
    else:
        payload = { 'query': query }
    
    try:
        res = requests.post(url=url, headers=headers, json=payload)
        res.raise_for_status()

        if res.json().get('errors'):
            raise ShopifyQueryError(f'There was an error with the GraphQL query: {str(res.json()['errors'])}')

    except HTTPError as e:
        if res.status_code < 500:
            current_app.logger.error(f"HTTP client error occurred: {e}")  # 4xx, 5xx errors raised by raise_for_status()
        else:
            current_app.logger.warning(f"HTTP server error occurred: {e}") 
        raise
    except ConnectionError as e: #TODO wait a bit and keep trying on >= 500 error, connection errors, timeout errors
        current_app.logger.warning(f"Connection error occurred: {e}")  # Network problems
        raise
    except Timeout as e:
        current_app.logger.warning(f"Timeout error occurred: {e}")  # Timeout
        raise
    except RequestException as e:
        current_app.logger.error(f"An error occurred: {e}")  # Catch-all for other request exceptions
        raise
    except ShopifyQueryError as e:
        current_app.logger.error(f"GraphQL query error occured: {e}")
        raise

    return res

def raise_for_user_errors(res: requests.Response, queried_field: str):
    """queried_field is the top level field of the query."""
    try:
        user_errors = res.json()['data'][queried_field]['userErrors']
    except KeyError:
        current_app.logger.error(f'All mutations should have "userError" field. response: {str(res.json())}')
        raise

    if len(user_errors) > 0:
        error_msg = f'There was an error in the mutation input: {str(user_errors)}'
        current_app.logger.error(error_msg)
        raise ShopifyUserError(error_msg)

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
