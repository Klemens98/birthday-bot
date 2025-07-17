"""Event handler module for managing Discord events."""
import logging
from services.notification_service import NotificationService
from services.birthday_service import BirthdayService

logger = logging.getLogger('BirthdayBot.EventHandler')

class EventHandler:
    def __init__(self, notification_service: NotificationService, birthday_service: BirthdayService):
        """Initialize event handler.
        
        Args:
            notification_service (NotificationService): Notification service instance
            birthday_service (BirthdayService): Birthday service instance
        """
        self.notification_service = notification_service
        self.birthday_service = birthday_service

    async def on_raw_reaction_add(self, payload, channel, bot_user):
        """Handle reaction add events.
        
        Args:
            payload: Discord reaction payload
            channel: Discord channel object
            bot_user: Bot's user object
        """
        if payload.user_id == bot_user.id:
            return
            
        logger.info(f"Reaction added - User: {payload.user_id}, Message: {payload.message_id}")
        if not channel:
            logger.warning(f"Could not find channel for reaction: {payload.channel_id}")
            return
            
        await self.notification_service.handle_reaction_add(
            channel, payload.user_id, payload.message_id, payload.emoji)

    async def on_raw_reaction_remove(self, payload, channel, bot_user):
        """Handle reaction remove events.
        
        Args:
            payload: Discord reaction payload
            channel: Discord channel object
            bot_user: Bot's user object
        """
        if payload.user_id == bot_user.id:
            return
            
        logger.info(f"Reaction removed - User: {payload.user_id}, Message: {payload.message_id}")
        if not channel:
            logger.warning(f"Could not find channel for reaction: {payload.channel_id}")
            return
            
        await self.notification_service.handle_reaction_remove(
            channel, payload.user_id, payload.message_id, payload.emoji)