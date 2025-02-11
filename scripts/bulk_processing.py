# For processing data obtained from the bulk_op_products bulk operation query in 
# app/shop/graphql_queries.py

import json
import pandas as pd
from collections import defaultdict

def read_jsonl(data_path: str) -> list[dict]:
    '''Reads JSONL data from storage service.'''
    with open(data_path, 'r') as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines]

def products_df(data_path: str) -> pd.DataFrame:
    '''
    Output columns:
    id, title, vendor, total_variants, metafields

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    '''
    products = {}
    
    for data in read_jsonl(data_path):
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
    return df

def variants_df(data_path: str) -> pd.DataFrame:
    '''
    Output columns:
    id, sku, cost_history, variant_id

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    '''
    variants = []
    
    for data in read_jsonl(data_path):
        if 'sku' in data:  # Variant entry
            variants.append({
                'id': data['id'],
                'sku': data['sku'],
                'cost_history': data['metafield'],
                'variant_id': data['__parentId']
            })
    
    df = pd.DataFrame(variants)
        
    return df

def vendors_df(data_path: str) -> pd.DataFrame:
    '''
    Output columns:
    number_of_products, number_of_variants, towns (town1;;state1::town2;;state2::etc), vendor

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    '''
    vendors = defaultdict(lambda: {'number_of_products': 0, 'number_of_variants': 0, 'towns': set()})
    products = products_df(data_path)

    for _, row in products.iterrows():
        vendor = row['vendor']
        vendors[vendor]['number_of_products'] += 1
        vendors[vendor]['number_of_variants'] += row['total_variants']
        metafields = row['metafields']

        pueblo, estado = '', ''
        for metafield in metafields:
            if metafield['namespace']=='custom' and metafield['key']=='pueblo':
                pueblo = metafield['value']
            if metafield['namespace']=='custom' and metafield['key']=='estado':
                estado = metafield['value']
        if pueblo or estado:
            vendors[vendor]['towns'].add((pueblo, estado))
    
    for name, details in vendors.items():
        details['vendor'] = name
        details['towns'] = '::'.join(';;'.join(town) for town in details['towns'])

    df = pd.DataFrame(vendors.values())

    return df

def towns_df(data_path: str) -> pd.DataFrame:
    '''
    All unique combinations of town and state.
    cols are 'pueblo', 'estado'
    '''
    vendors = vendors_df(data_path)

    town_state_pairs = set()
    for town_string in vendors['towns']:
        if town_string:
            town_state_pairs.update(tuple(town.split(';;')) for town in town_string.split('::'))

    df = pd.DataFrame(town_state_pairs, columns=['pueblo', 'estado'])

    return df
    

if __name__=='__main__':
    JSONL_PATH = '../data/bulk/bulk-5095337427241.jsonl'

    towns_df(JSONL_PATH).to_csv('../data/bulk/pueblos.csv')
