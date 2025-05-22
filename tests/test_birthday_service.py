"""Tests for the birthday service module."""
import pytest
from datetime import datetime
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