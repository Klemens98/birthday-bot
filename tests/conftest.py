"""Test configuration and fixtures."""
import os
import sys
import pytest
import tempfile
from datetime import datetime
from typing import Optional
from unittest.mock import Mock, MagicMock

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class MockDatabaseService:
    """Mock database service for testing."""
    
    def __init__(self):
        self.table_name = "test_birthdays"
        self._data = {}
        self._dm_preferences = {}
    
    def set_birthday(self, user_id: int, username: str, birthday: datetime, 
                    firstname: Optional[str] = None, lastname: Optional[str] = None, 
                    dm_enabled: bool = False):
        """Mock set_birthday method."""
        self._data[user_id] = {
            'username': username,
            'birthday': birthday,
            'firstname': firstname,
            'lastname': lastname,
            'dm_preference': dm_enabled
        }
        self._dm_preferences[user_id] = dm_enabled
    
    def add_birthday(self, user_id: int, username: str, birthday: datetime,
                    firstname: Optional[str] = None, lastname: Optional[str] = None, dm_enabled: bool = False):
        """Mock add_birthday method for backward compatibility."""
        self.set_birthday(user_id, username, birthday, firstname, lastname, dm_enabled)
    
    def get_todays_birthdays(self):
        """Mock get_todays_birthdays method."""
        today = datetime.now().date()
        results = []
        for user_id, data in self._data.items():
            if data['birthday']:
                birthday_date = data['birthday'].date()
                # Check if birthday (month and day) matches today
                if birthday_date.month == today.month and birthday_date.day == today.day:
                    results.append((
                        user_id,
                        data['username'],
                        data['firstname'],
                        data['lastname'],
                        data['birthday'],
                        data['dm_preference']
                    ))
        return results
    
    def get_upcoming_birthdays(self, limit: int = 5):
        """Mock get_upcoming_birthdays method."""
        today = datetime.now().date()
        birthdays_with_next_date = []
        
        for user_id, data in self._data.items():
            if data['birthday']:
                birthday = data['birthday'].date()
                # Calculate next birthday
                this_year_birthday = birthday.replace(year=today.year)
                if this_year_birthday >= today:
                    next_birthday = this_year_birthday
                else:
                    next_birthday = birthday.replace(year=today.year + 1)
                
                birthdays_with_next_date.append((
                    next_birthday,
                    user_id,
                    data['username'],
                    data['firstname'],
                    data['lastname'],
                    data['birthday'],
                    data['dm_preference']
                ))
        
        # Sort by next birthday date and return the requested number
        birthdays_with_next_date.sort(key=lambda x: x[0])
        return [entry[1:] for entry in birthdays_with_next_date[:limit]]
    
    def get_all_users(self):
        """Mock get_all_users method."""
        users = []
        for user_id, data in self._data.items():
            users.append((
                user_id,
                data['username'],
                data['firstname'],
                data['lastname']
            ))
        # Sort by username to match the real implementation
        users.sort(key=lambda x: x[1])
        return users
    
    def get_users_with_dm_enabled(self):
        """Mock get_users_with_dm_enabled method."""
        return [(user_id,) for user_id, enabled in self._dm_preferences.items() if enabled]
    
    def update_dm_preference(self, user_id: int, enabled: bool):
        """Mock update_dm_preference method."""
        self._dm_preferences[user_id] = enabled
        if user_id in self._data:
            self._data[user_id]['dm_preference'] = enabled
    
    def update_username(self, user_id: int, username: str):
        """Mock update_username method."""
        if user_id in self._data:
            self._data[user_id]['username'] = username

@pytest.fixture
def test_db():
    """Create a mock test database."""
    return MockDatabaseService()

@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        'DISCORD': {
            'TOKEN': 'test-token',
            'APPLICATION_ID': 123456789,
            'CHANNEL_ID': 987654321
        },
        'TIMEZONE': 'Europe/Berlin'
    }