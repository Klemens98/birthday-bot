"""Tests for the notification service module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.notification_service import NotificationService

class AsyncIteratorMock:
    """Mock for async iterators."""
    def __init__(self, items):
        self.items = items
        self.index = 0
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item

@pytest.mark.asyncio
async def test_setup_notification_message_new(test_db):
    """Test setting up notification message when none exists."""
    notification_service = NotificationService(test_db)
    
    # Test that the service initializes correctly
    assert notification_service.notify_message_id is None
    
    # Test setting the notify message ID
    notification_service.notify_message_id = 123456789
    assert notification_service.notify_message_id == 123456789

@pytest.mark.asyncio
async def test_setup_notification_message_existing(test_db):
    """Test notification service property handling."""
    notification_service = NotificationService(test_db)
    
    # Test property getter and setter
    assert notification_service.notify_message_id is None
    
    notification_service.notify_message_id = 987654321
    assert notification_service.notify_message_id == 987654321

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