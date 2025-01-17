from typing import Union
import requests
from numpy import nan
# -------------- Not for testing -------------- #
from app import app
import app.shop.graphql_queries as q

STORE = app.config['SHOPIFY_STORE']
API_TOKEN = app.config['SHOPIFY_API_TOKEN']
LOCATION_ID = app.config['SHOPIFY_LOCATION_ID']
# -------------- Not for testing -------------- #
# -------------- Just for testing -------------- #
# import graphql_queries as q
# import os
# from dotenv import load_dotenv
# load_dotenv('../')
# STORE = os.getenv('TEST_SHOPIFY_STORE')
# API_TOKEN = os.getenv('TEST_SHOPIFY_API_TOKEN')
# LOCATION_ID = os.getenv('TEST_SHOPIFY_LOCATION_ID') 
# -------------- Just for testing -------------- #

def graphql_query(query: str, variables: dict = None) -> requests.Response:
    """
    To query the Shopify GraphQL API. Use with both queries and mutations.
    Returns response as is. Does not check for errors.
    
    Params
    - query is any valid GraphQL query. See example below.

    Example
    query = '''\\
    {
        products(first: 3) {
            edges {
            node {
                id
                title
            }
            }
        }
    }
    '''
    response = graphql_query(query=query)
    """
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
        
    res = requests.post(url=url, headers=headers, json=payload)

    return res

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
            "productId": variant['product']['id']
        }
        variants.append(variant_data)

    return variants

def set_variant_cost(inventory_item_id:str, cost:float) -> requests.Response:
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

    return res

def set_variant_price(product_id:str, variant_id:Union[str, list[str]], price:Union[float, list[float]]) -> requests.Response:
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

    return res

def adjust_variant_quantities(changes: list[dict], reason: str = 'received', name: str = 'available') -> requests.Response:
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
    
    # TODO: this will be unsuccessful if:
    # 1. response is not 200 or
    # 2. response is 200 but comes back with 'userErrors' != [] (not an empty list)
    print("\n\n", LOCATION_ID)
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

    return res
