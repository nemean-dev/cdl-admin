from time import sleep
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from flask import current_app

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
    
    try_again, try_count = True, 0
    while try_again:
        try_again=False
        try:
            res = requests.post(url=url, 
                                headers=headers, 
                                json=payload, 
                                timeout=(5, 15))
            res.raise_for_status()

            if res.json().get('errors'):
                raise ShopifyQueryError(f'There was an error with the GraphQL query: {str(res.json()['errors'])}')

        except HTTPError as e:
            if res.status_code == 429:
                try_again = True
                sleep(2)
                current_app.logger.warning("429 Response: Too many requests. Waiting 2 seconds...")
                if try_count >= 5:
                    raise
            elif res.status_code < 500:
                current_app.logger.error(f"HTTP client error occurred: {e}")
                raise
            else:
                current_app.logger.warning(f"HTTP server error occurred, will try again in 3 seconds. Error: {e}") 
                try_again = True
                sleep(3)
        except ConnectionError as e:
            current_app.logger.warning(f"Connection error occurred. Trying again in 3 seconds: {e}")
            sleep(3)
            try_again = True
            if try_count >= 7: 
                raise
        except Timeout as e:
            current_app.logger.warning(f"Timeout error occurred: {e}")
            if try_count >= 2:
                raise
        except RequestException as e:
            current_app.logger.error(f"An error occurred: {e}")
            raise
        except ShopifyQueryError as e:
            current_app.logger.error(f"GraphQL query error occured: {e}")
            raise
        else:
            throttle_management(res)
        finally:
            try_count+=1

    return res # TODO why not just return res.json() ?

def raise_for_user_errors(res: requests.Response, queried_field: str):
    """
    This function should only be used with mutations.
    queried_field is the top level field of the mutation; containing the 'userErrors' field.
    """
    try:
        user_errors = res.json()['data'][queried_field]['userErrors']
    except KeyError:
        current_app.logger.error(f'All mutations should have "userError" field. response: {str(res.json())}')
        raise

    if len(user_errors) > 0:
        error_msg = f'There was an error in the mutation input: {str(user_errors)}'
        current_app.logger.error(error_msg)
        raise ShopifyUserError(error_msg) 
        # TODO: instead of raising for user errors everywhere, make 
        # graphql_query() identify if the request, mutation name (or write it in 
        # the graphql_queries.py file) is a mutation and raise for user errors 
        # if it is.

def throttle_management(response: requests.Response, default_seconds=0):
    try:
        query_cost_info = response.json()['extensions']['cost']
        requested_query_cost = query_cost_info['requestedQueryCost']
        available = query_cost_info['throttleStatus']['currentlyAvailable']
        restore_rate = query_cost_info['throttleStatus']['restoreRate']
        
        if requested_query_cost > available:
            wait_time = (requested_query_cost - available) // restore_rate + 1
            current_app.logger.info(f"Insufficient throttle: needed {requested_query_cost}, available {available}. Waiting for {wait_time} seconds.")
            sleep(wait_time)
        else:
            current_app.logger.debug("Sufficient throttle available; no wait required.")

    except KeyError:
        current_app.logger.warning("No query cost info in response, skipping throttle management. Waiting for the default time.")
        sleep(default_seconds)

def start_bulk_operation(query: str, variables: dict = None) -> str:
    '''Returns operation id. Raises for user errors.'''
    res = graphql_query(query, variables)
    raise_for_user_errors(res, 'bulkOperationRunQuery')

    id = res.json()['data']['bulkOperationRunQuery']['bulkOperation']['id']
    current_app.logger.info(f"Started bulk operation: {id}")

    return id

def poll_bulk_operation(id) -> str | None:
    '''
    If the bulk operation has been completed, returns the download url of the data.
    Otherwise, returns None.

    Example usage:
    ```
    while True:
        sleep(5)
        url = poll_bulk_operation(id)
        if url:
            break
    ```
    '''
    poll_bulk_op = \
'''
query {
    currentBulkOperation {
        id
        status
        errorCode
        createdAt
        completedAt
        objectCount
        fileSize
        url
        partialDataUrl
    }
}
'''
    res = graphql_query(poll_bulk_op).json()
    status = res['data']['currentBulkOperation']['status']
    if status == 'COMPLETED':
        current_app.logger.info(f"Bulk operation complete.")
        return res['data']['currentBulkOperation']['url']
    else:
        return None

