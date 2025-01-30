import re
from datetime import datetime, timezone
from unidecode import unidecode

def extended_compare(str1: str, str2: str) -> bool:
    '''
    If strings are similar, returns True.
    
    case insensitive compare ignoring accents and trailing and multiple consecutive blank characters.
    '''
    return unidecode(extra_strip(str1).lower()) == unidecode(extra_strip(str2).lower())

def is_multiline(text: str) -> bool:
    '''Checks if the given string contains multiple lines.'''
    if not isinstance(text, str):
        raise TypeError("Expected string.")
    
    return '\n' in text or '\r' in text

def extra_strip(string: str) -> str:
    '''
    removes trailing and multiple consecutive whitespace characters
    e.g. extra_strip("hello    world ") -> "hello world"
    '''
    return re.sub(r'\s+', ' ', string).strip()

def simple_lower_ascii(string):
    '''
    returns string lowered, with no accents, and no multiple consecutive 
    whitespace characters
    '''
    return unidecode(extra_strip(string).lower())

def remove_whitespace(string: str) -> str:
    '''
    removes all whitespace
    '''
    return re.sub(r'\s', '', string)

def get_datestring(date: datetime= None) -> str:
    '''Returns datestring YYYY-MM-DD. If no date is provided, datestring represents current date.'''
    if not date:
        date = datetime.now(timezone.utc)

    formatted_date = date.strftime('%Y-%m-%d')

    return formatted_date

def get_shopify_timestring(time: datetime = None) -> str:
    '''Returns timestring YYYY-MM-DDTHH:MM:SSZ. If no time is provided, timestring represents current time.'''
    if not time:
        time = datetime.now(timezone.utc)

    formatted_time = time.strftime('%Y-%m-%dT%H:%M:%SZ')

    return formatted_time

def validate_shopify_timestring(timestring: str) -> bool:
    '''Validates if the input string is in the Shopify required format: YYYY-MM-DDTHH:MM:SSZ'''
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
    return bool(re.match(pattern, timestring))

def validate_spanish_characters(string: str) -> bool:
    '''
    Checks if the given string contains only valid Spanish characters.
    Raises a warning if an invalid character is found.
    '''
    if not isinstance(string, str):
        raise TypeError("Expected a string.")

    valid_chars = r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ/\s.,;¡!¿?()\"'-]*$"
    
    return re.fullmatch(valid_chars, string) is not None

