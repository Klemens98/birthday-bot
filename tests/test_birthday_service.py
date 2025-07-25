"""Tests for the birthday service module."""
import pytest
from datetime import datetime, timedelta
import pytz
from unittest.mock import Mock, AsyncMock
from services.birthday_service import BirthdayService
from utils.date_utils import get_berlin_now

@pytest.mark.asyncio
async def test_process_todays_birthdays(test_db):
    """Test processing of today's birthdays."""
    # Setup
    birthday_service = BirthdayService(test_db)
    
    # Mock Discord objects
    guild = Mock()
    channel = AsyncMock()
    bot_user = Mock()
    
    # Add test birthday for today (using current date)
    today = datetime.now()
    test_db.add_birthday(
        123456789, 
        "testuser", 
        today,  # Use today's date directly
        "Test", 
        "User"
    )
    
    # Process birthdays
    messages = await birthday_service.process_todays_birthdays(guild, channel, bot_user)
    
    # Verify results
    assert len(messages) == 1
    assert "Test" in messages[0]
    assert "Alles Gute zum Geburtstag" in messages[0]
    channel.send.assert_called_once()

@pytest.mark.asyncio
async def test_process_todays_birthdays_no_birthdays(test_db):
    """Test processing when there are no birthdays today."""
    # Setup
    birthday_service = BirthdayService(test_db)
    
    # Mock Discord objects
    guild = Mock()
    channel = AsyncMock()
    bot_user = Mock()
    
    # Add birthday for a different date (yesterday)
    yesterday = datetime.now() - timedelta(days=1)
    test_db.add_birthday(
        123456789,
        "testuser",
        yesterday,
        "Test",
        "User"
    )
    
    # Process birthdays
    messages = await birthday_service.process_todays_birthdays(guild, channel, bot_user)
    
    # Verify results
    assert len(messages) == 0
    channel.send.assert_not_called()

@pytest.mark.asyncio
async def test_process_todays_birthdays_with_dm_notifications(test_db):
    """Test processing birthdays with DM notifications enabled."""
    # Setup
    birthday_service = BirthdayService(test_db)
    
    # Mock Discord objects
    guild = Mock()
    channel = AsyncMock()
    bot_user = AsyncMock()
    notif_user = AsyncMock()
    bot_user.fetch_user.return_value = notif_user
    
    # Add test birthday for today
    today = datetime.now()
    test_db.add_birthday(
        123456789, 
        "birthdayuser", 
        today,  # Today's birthday
        dm_enabled=False
    )
    test_db.add_birthday(
        987654321,
        "notifuser",
        datetime(2000, 1, 1),  # Different date
        dm_enabled=True
    )
    
    # Process birthdays
    messages = await birthday_service.process_todays_birthdays(guild, channel, bot_user)
    
    # Verify results
    assert len(messages) == 1
    channel.send.assert_called_once()
    bot_user.fetch_user.assert_called_once_with(987654321)
    notif_user.send.assert_called_once()

def test_get_upcoming_birthdays(test_db):
    """Test getting upcoming birthdays."""
    # Add test birthdays with different dates
    today = datetime.now()
    
    # Birthday tomorrow
    test_db.add_birthday(
        111111111,
        "user1",
        today + timedelta(days=1),
        "First1",
        "Last1"
    )
    
    # Birthday in a week
    test_db.add_birthday(
        222222222,
        "user2", 
        today + timedelta(days=7),
        "First2",
        "Last2"
    )
    
    # Birthday last month (should appear for next year)
    test_db.add_birthday(
        333333333,
        "user3",
        today - timedelta(days=30),
        "First3",
        "Last3"
    )
    
    # Get upcoming birthdays
    upcoming = test_db.get_upcoming_birthdays(5)
    
    # Should get results
    assert len(upcoming) >= 2
    
    # First result should be the soonest birthday (tomorrow)
    first_birthday = upcoming[0]
    assert first_birthday[1] == "user1"  # username
    assert first_birthday[2] == "First1"  # firstname

def test_get_upcoming_birthdays_limit(test_db):
    """Test that the limit parameter works correctly."""
    today = datetime.now()
    
    # Add 10 birthdays
    for i in range(10):
        test_db.add_birthday(
            i,
            f"user{i}",
            today + timedelta(days=i+1),
            f"First{i}",
            f"Last{i}"
        )
    
    # Test different limits
    upcoming_3 = test_db.get_upcoming_birthdays(3)
    assert len(upcoming_3) == 3
    
    upcoming_5 = test_db.get_upcoming_birthdays(5)
    assert len(upcoming_5) == 5
    
    upcoming_all = test_db.get_upcoming_birthdays(20)
    assert len(upcoming_all) == 10  # Only 10 exist

def test_get_all_users_for_fuzzy_matching(test_db):
    """Test getting all users for fuzzy matching."""
    # Add test users with different names
    test_db.add_birthday(
        111111111,
        "john_doe",
        datetime(2000, 1, 1),
        "John",
        "Doe"
    )
    
    test_db.add_birthday(
        222222222,
        "jane_smith",
        datetime(2000, 2, 2),
        "Jane",
        "Smith"
    )
    
    test_db.add_birthday(
        333333333,
        "bob_wilson",
        datetime(2000, 3, 3),
        "Bob",
        None  # No last name
    )
    
    # Get all users
    all_users = test_db.get_all_users()
    
    # Should get all users
    assert len(all_users) == 3
    
    # Check first user
    user1 = all_users[0]
    assert user1[0] == 333333333  # user_id (sorted by username, so bob_wilson comes first)
    assert user1[1] == "bob_wilson"  # username
    assert user1[2] == "Bob"  # firstname
    assert user1[3] is None  # lastname
    
    # Check second user
    user2 = all_users[1]
    assert user2[0] == 222222222  # user_id
    assert user2[1] == "jane_smith"  # username
    assert user2[2] == "Jane"  # firstname
    assert user2[3] == "Smith"  # lastname