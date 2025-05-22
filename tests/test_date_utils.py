"""Tests for the date utility functions."""
from datetime import datetime
import pytz
import pytest
from utils.date_utils import get_berlin_now, parse_date

def test_get_berlin_now():
    """Test getting current time in Berlin timezone."""
    now = get_berlin_now()
    assert isinstance(now, datetime)
    assert now.tzinfo == pytz.timezone('Europe/Berlin')

def test_parse_date_valid():
    """Test parsing valid date string."""
    date = parse_date('01.12.2023')
    assert isinstance(date, datetime)
    assert date.day == 1
    assert date.month == 12
    assert date.year == 2023

def test_parse_date_invalid():
    """Test parsing invalid date strings."""
    with pytest.raises(ValueError):
        parse_date('invalid')
    
    with pytest.raises(ValueError):
        parse_date('2023-12-01')  # Wrong format
    
    with pytest.raises(ValueError):
        parse_date('32.12.2023')  # Invalid day
    
    with pytest.raises(ValueError):
        parse_date('01.13.2023')  # Invalid month