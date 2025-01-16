import pandas as pd
import requests
from app import app

TESTING_QUERY = '''
query Test {
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

def graphql_query(query: str, input: str = None) -> requests.Response:
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
    url = f"https://{app.config['SHOPIFY_STORE']}.myshopify.com/admin/api/2025-01/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": app.config['SHOPIFY_API_TOKEN'],
    }

    if input:
        payload = {
            'query': query,
            'input': input
        }
        res = requests.post(url=url, headers=headers, json=payload)
    else:
        res = requests.post(url=url, headers=headers, json={"query": query})

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
    query = \
"""
{
  productVariants(first: 3, query: "sku:%s") {
    nodes {
      id
      product {
        vendor
      }
      price
      displayName
      inventoryItem {
        id
        unitCost {
          amount
        }
      }
    }
  }
}
""" % sku

    res = graphql_query(query)
    data = res.json()['data']

    variants = []
    for variant in data['productVariants']['nodes']:
        variant_data = {
            "sku": sku,
            "variantId": variant['id'],
            "displayName": variant['displayName'],
            "vendor": variant['product']['vendor'],
            "price": variant['price'],
            "unitCost": variant['inventoryItem']['unitCost']['amount'],
            "inventoryItemId": variant['inventoryItem']['id'],
        }
        variants.append(variant_data)

    return variants