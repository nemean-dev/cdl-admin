# For processing of the data obtained from the following Shopify bulk operation query:
'''
mutation {
  bulkOperationRunQuery(
    query: """
      {
        products {
          edges{
            node {
              id
              title
              vendor
              metafields {
                edges {
                  node {
                    namespace
                    key
                    value
                  }
                }
              }
              variants {
                edges {
                  node {
                    id
                    sku
                    metafield (namespace: "custom", key: "cost_history") {
                      key
                      value
                    }
                  }
                }
              }
            }
          }
        }
      }
    """
  ) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
'''
import os
import json
import pandas as pd
from flask import current_app
from collections import defaultdict

BASE_PATH = os.path.join(current_app.config['DATA_DIR'], 'bulk')
JSONL_PATH = os.path.join(BASE_PATH, 'bulk_operation.jsonl')

def products_df(path: str = None) -> pd.DataFrame:
    '''id, title, vendor, total_variants, metafields'''
    products = {}
    
    with open(JSONL_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            
            if 'vendor' in data:  # Product entry
                product_id = data['id']
                products[product_id] = {
                    'id': product_id,
                    'title': data['title'],
                    'vendor': data['vendor'],
                    'total_variants': 0,
                    'metafields': [],
                }
            elif 'namespace' in data and data['__parentId'] in products:  # product metafield
                product_id = data['__parentId']
                products[product_id]['metafields'].append({
                    'namespace': data.get('namespace'),
                    'key': data.get('key'),
                    'value': data.get('value')
                })
            elif 'sku' in data: #product variant
                product_id = data['__parentId']
                products[product_id]['total_variants'] += 1
    
    df = pd.DataFrame(products.values())
    if path:
        df.to_csv(path, index=False)
    return df

def variants_df(path: str = None) -> pd.DataFrame:
    variants = []
    
    with open(JSONL_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            
            if 'sku' in data:  # Variant entry
                variants.append({
                    'id': data['id'],
                    'sku': data['sku'],
                    'cost_history': data['metafield'],
                    'product_id': data['__parentId']
                })
    
    df = pd.DataFrame(variants)
    if path:
        df.to_csv(path, index=False)
    return df

def vendors_df(path: str = None) -> pd.DataFrame:
    vendors = defaultdict(lambda: {'number_of_products': 0, 'number_of_variants': 0, 'towns': set()})
    products = products_df()

    for _, row in products.iterrows():
        vendor = row['vendor']
        vendors[vendor]['number_of_products'] += 1
        vendors[vendor]['number_of_variants'] += row['total_variants']
        metafields = row['metafields']

        pueblo, estado = None, None
        for metafield in metafields:
            if metafield['namespace']=='custom' and metafield['key']=='pueblo':
                pueblo = metafield['value']
            if metafield['namespace']=='custom' and metafield['key']=='estado':
                estado = metafield['value']
        if pueblo or estado:
            vendors[vendor]['towns'].add((pueblo, estado))
    
    for name, details in vendors.items():
        details['vendor'] = name

    df = pd.DataFrame(vendors.values())
    df['towns'] = df['towns'].apply(list)
    if path:
        df.to_csv(path, index=False)
    return df


if __name__=='__main__':
    import os
    os.makedirs(BASE_PATH, exist_ok=True)

    products_df(os.path.join(BASE_PATH, 'products.csv'))
    variants_df(os.path.join(BASE_PATH, 'variants.csv'))
    vendors_df(os.path.join(BASE_PATH, 'vendors.csv'))
