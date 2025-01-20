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
