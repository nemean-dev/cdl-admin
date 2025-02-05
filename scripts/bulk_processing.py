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
import json
import pandas as pd
from collections import defaultdict

def products_df(data_path: str, output_path: str = None) -> pd.DataFrame:
    '''
    Output columns:
    id, title, vendor, total_variants, metafields

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    - output_path: if given, will write csv to this output path.
    '''
    products = {}
    
    with open(data_path, 'r', encoding='utf-8') as f:
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
    if output_path:
        df.to_csv(output_path, index=False)
    return df

def variants_df(data_path: str, output_path: str = None) -> pd.DataFrame:
    '''
    Output columns:
    id, sku, cost_history, variant_id

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    - output_path: if given, will write csv to this output path.
    '''
    variants = []
    
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            
            if 'sku' in data:  # Variant entry
                variants.append({
                    'id': data['id'],
                    'sku': data['sku'],
                    'cost_history': data['metafield'],
                    'variant_id': data['__parentId']
                })
    
    df = pd.DataFrame(variants)
    if output_path:
        df.to_csv(output_path, index=False)
    return df

def vendors_df(data_path: str, output_path: str = None) -> pd.DataFrame:
    '''
    Output columns:
    number_of_products, number_of_variants, towns (string repr of list), vendor

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    - output_path: if given, will write csv to this output path.
    '''
    vendors = defaultdict(lambda: {'number_of_products': 0, 'number_of_variants': 0, 'towns': set()})
    products = products_df(data_path)

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
    if output_path:
        df.to_csv(output_path, index=False)
    return df


if __name__=='__main__':
    import os

    BASE_PATH = os.path.join('data/', 'bulk')
    JSONL_PATH = os.path.join(BASE_PATH, 'bulk_operation.jsonl')

    products_df(JSONL_PATH, os.path.join(BASE_PATH, 'products.csv'))
    variants_df(JSONL_PATH, os.path.join(BASE_PATH, 'variants.csv'))
    vendors_df(JSONL_PATH, os.path.join(BASE_PATH, 'vendors.csv'))
