# For processing data obtained from the bulk_op_products bulk operation query in 
# app/shop/graphql_queries.py

import json
import ast
import pandas as pd
import time
from collections import defaultdict
from threading import Thread
import requests
from flask import current_app
import sqlalchemy as sa
from app import storage_service, db
from app.models import Vendor, State, Town, ShopifyVendor
from app.utils import simple_lower_ascii
from app.integrations.shopify import start_bulk_operation, poll_bulk_operation
from app.shop.graphql_queries import bulk_op_products

def async_update_db():
    '''
    Asynchronously query shopify via a bulk operation and when the file is ready, 
    update the vendors table.
    '''
    id = start_bulk_operation(bulk_op_products)

    def poll():
        while True:
            time.sleep(5)
            url = poll_bulk_operation(id)
            if url:
                break

        file_path = "jsonl/products.jsonl"
        file_content = requests.get(url).content

        current_app.logger.info("File downloaded. Processing...")
        data = [json.loads(line) for line in file_content.splitlines()]
        
        update_database(data)

        current_app.logger.info('Uploading jsonl to S3')
        storage = storage_service()
        storage.upload_text(file_path, file_content) 
        # TODO every time a file is uploaded, create a record in the File table

    thread = Thread(target=poll, daemon=True,)
    thread.start()

def read_jsonl(data_path: str) -> list[dict]:
    '''Reads JSONL data from storage service.'''
    storage = storage_service()
    data = storage.download_text(data_path)
    return [json.loads(line) for line in data.splitlines()]

def products_df(data: list[dict]) -> pd.DataFrame:
    '''
    Output columns:
    id, title, vendor, total_variants, metafields

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    '''
    products = {}
    
    for row in data:
        if 'vendor' in row:  # Product entry
            product_id = row['id']
            products[product_id] = {
                'id': product_id,
                'title': row['title'],
                'vendor': row['vendor'],
                'total_variants': 0,
                'metafields': [],
            }
        elif 'namespace' in row and row['__parentId'] in products:  # product metafield
            product_id = row['__parentId']
            products[product_id]['metafields'].append({
                'namespace': row.get('namespace'),
                'key': row.get('key'),
                'value': row.get('value')
            })
        elif 'sku' in row: #product variant
            product_id = row['__parentId']
            products[product_id]['total_variants'] += 1
    
    df = pd.DataFrame(products.values())
    return df

def variants_df(data: list[dict]) -> pd.DataFrame:
    '''
    Output columns:
    id, sku, cost_history, variant_id

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    '''
    variants = []
    
    for row in data:
        if 'sku' in row:  # Variant entry
            variants.append({
                'id': row['id'],
                'sku': row['sku'],
                'cost_history': row['metafield'],
                'variant_id': row['__parentId']
            })
    
    df = pd.DataFrame(variants)
        
    return df

def vendors_df(data: list[dict]) -> pd.DataFrame:
    '''
    Output columns:
    number_of_products, number_of_variants, towns (town1;;state1::town2;;state2::etc), vendor

    Params:
    - data_path: should point to a jsonl file representing bulk operation result
    '''
    vendors = defaultdict(lambda: {'number_of_products': 0, 'number_of_variants': 0, 'towns': set()})
    products = products_df(data)

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

def locations_df(data: list[dict]) -> pd.DataFrame:
    '''
    All unique combinations of town and state.
    cols are 'pueblo', 'estado'
    '''
    vendors = vendors_df(data)

    town_state_pairs = set()
    for town_string in vendors['towns']:
        if town_string:
            town_state_pairs.update(tuple(town.split(';;')) for town in town_string.split('::'))

    df = pd.DataFrame(town_state_pairs, columns=['pueblo', 'estado'])

    return df

def update_database(data: list[dict]):
    '''Updates vendor, pueblo, estado tables.'''
    locations = locations_df(data)
    update_locations(locations)
    vendors = vendors_df(data)
    update_vendors(vendors)

def update_locations(locations: pd.DataFrame):
    current_app.logger.info('Updating locations...')

    df = df.replace({float('nan'): None})
    for _, row in locations.iterrows():
        state_name = row['estado'] if row['estado'] else '(vacío)'
        town_name = row['pueblo'] if row['pueblo'] else '(vacío)'

        state = db.session.scalar(sa.select(State).where(State.name == state_name))
        if not state:
            new_state = State(name=state_name, code=state_name)
            db.session.add(new_state)
            db.session.commit()
        
        town = db.session.scalar(sa.select(Town).where(
            Town.name == town_name,
            Town.state == state))
        if not town:
            new_town = Town(name=town_name, state=state)
            db.session.add(new_town)
            db.session.commit()

def update_vendors(vendors_df: pd.DataFrame):
    '''
    Load vendors from a CSV file into the db.
    Meant for use with data generated by the vendors_df script from bulk_processing.
    '''
    # Remove rows if vendor is nan/empty
    current_app.logger.info('Updating vendors...')

    vendors = vendors_df.copy() #TODO why not just mutate? use original to create csv file?
    vendors = vendors.dropna(subset=['vendor'])
    vendors = vendors[vendors['vendor'].str.strip() != '']

    for _, row in vendors.iterrows():
        vendor_name = row['vendor']
        vendor_compare_name = simple_lower_ascii(vendor_name)

        towns = []
        for town_name, state_name in [tuple(pair.split(";;")) for pair in row['towns'].split("::")]:
            town = db.session.scalar(sa.select(Town).where(
                Town.name == town_name,
                Town.state.name == state_name))
            towns.append(town)

        current_app.logger.info('Searching for vendor with similar name to ' + vendor_name)
        found_vendor = db.session.scalar(sa.select(Vendor).where(Vendor.compare_name == vendor_compare_name))

        if not found_vendor:
            vendor = Vendor()
            vendor.set_name(vendor_name)
            current_app.logger.info(f'Created new vendor {vendor}')

        else:
            vendor = found_vendor

        vendor.total_products = row['number_of_products']
        vendor.total_variants = row['number_of_variants']
        if not vendor.town:
            vendor.town = towns[0]
        for town in towns:
            vendor.add_shopify_town(town)    

        db.session.add(vendor)

        shopify_vendor = db.session.scalar(sa.select(ShopifyVendor).where(
            ShopifyVendor.name == vendor_name))
        if not shopify_vendor:
            new_shopify_vendor = ShopifyVendor(name=vendor_name, vendor=vendor)
            db.session.add(new_shopify_vendor)

        db.session.commit()
