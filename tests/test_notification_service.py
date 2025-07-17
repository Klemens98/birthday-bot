"""Tests for the notification service module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.notification_service import NotificationService

@pytest.mark.asyncio
async def test_setup_notification_message_new(test_db):
    """Test setting up notification message when none exists."""
    notification_service = NotificationService(test_db)
    channel = AsyncMock()
    message = AsyncMock()
    channel.history.return_value.__aiter__.return_value = []
    channel.send.return_value = message
    
    # Test setup
    result = await notification_service.setup_notification_message(channel)
    
    # Verify results
    assert result is True
    channel.send.assert_called_once()
    message.add_reaction.assert_called_once_with("✅")
    message.pin.assert_called_once()
    assert notification_service.notify_message_id == message.id

@pytest.mark.asyncio
async def test_setup_notification_message_existing(test_db):
    """Test setting up notification message when one already exists."""
    notification_service = NotificationService(test_db)
    channel = AsyncMock()
    existing_message = AsyncMock()
    existing_message.content = "Geburtstags-Benachrichtigungen"
    existing_message.id = 123456789
    channel.history.return_value.__aiter__.return_value = [existing_message]
    
    # Test setup
    result = await notification_service.setup_notification_message(channel)
    
    # Verify results
    assert result is True
    channel.send.assert_not_called()
    assert notification_service.notify_message_id == existing_message.id

@pytest.mark.asyncio
async def test_handle_reaction_add(test_db):
    """Test handling reaction add event."""
    notification_service = NotificationService(test_db)
    channel = AsyncMock()
    message = AsyncMock()
    message.content = "Geburtstags-Benachrichtigungen"
    channel.fetch_message.return_value = message
    
    # Test reaction handling
    await notification_service.handle_reaction_add(channel, 123456789, 987654321, "✅")
    
    # Verify database was updated
    assert test_db.get_users_with_dm_enabled() == [(123456789,)]

@pytest.mark.asyncio
async def test_handle_reaction_remove(test_db):
    """Test handling reaction remove event."""
    notification_service = NotificationService(test_db)
    channel = AsyncMock()
    message = AsyncMock()
    message.content = "Geburtstags-Benachrichtigungen"
    channel.fetch_message.return_value = message
    
    # Add user with DM enabled first
    test_db.update_dm_preference(123456789, True)
    
    # Test reaction handling
    await notification_service.handle_reaction_remove(channel, 123456789, 987654321, "✅")
    
    # Verify database was updated
    assert test_db.get_users_with_dm_enabled() == []

@pytest.mark.asyncio
async def test_test_dm(test_db):
    """Test sending test DM."""
    notification_service = NotificationService(test_db)
    user = AsyncMock()
    
    # Test successful DM
    result = await notification_service.test_dm(user)
    assert result is True
    user.send.assert_called_once()
    
    # Test failed DM
    user.send.side_effect = Exception("Failed to send DM")
    result = await notification_service.test_dm(user)
    assert result is False