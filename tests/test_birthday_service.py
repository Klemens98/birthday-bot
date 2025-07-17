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
    
    # Add test birthday
    now = get_berlin_now()
    test_db.add_birthday(
        123456789, 
        "testuser", 
        datetime(now.year, now.month, now.day), 
        "Test", 
        "User"
    )
    
    # Process birthdays
    messages = await birthday_service.process_todays_birthdays(guild, channel, bot_user)
    
    # Verify results
    assert len(messages) == 1
    assert "Test User" in messages[0]
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
    
    # Add test birthday and notification user
    now = get_berlin_now()
    test_db.add_birthday(
        123456789, 
        "birthdayuser", 
        datetime(now.year, now.month, now.day),
        dm_enabled=False
    )
    test_db.add_birthday(
        987654321,
        "notifuser",
        datetime(2000, 1, 1),
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