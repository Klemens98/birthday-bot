"""Date utility functions for birthday-related operations."""
from datetime import datetime
import pytz

def get_berlin_now():
    """Get current datetime in Berlin timezone.
    
    Returns:
        datetime: Current datetime in Europe/Berlin timezone
    """
    berlin_tz = pytz.timezone('Europe/Berlin')
    return datetime.now(berlin_tz).replace(tzinfo=berlin_tz)

def parse_date(date_str: str) -> datetime:
    """Parse a date string in DD.MM.YYYY format.
    
    Args:
        date_str (str): Date string in DD.MM.YYYY format
        
    Returns:
        datetime: Parsed datetime object
        
    Raises:
        ValueError: If date string is invalid
    """
    try:
        return datetime.strptime(date_str, '%d.%m.%Y')
    except ValueError as e:
        raise ValueError("Invalid date format. Please use DD.MM.YYYY") from e