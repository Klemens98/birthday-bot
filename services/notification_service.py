"""Service for managing birthday notifications."""
import logging
import discord
from database import DatabaseService  # Changed to absolute import
from datetime import datetime

logger = logging.getLogger('BirthdayBot.NotificationService')

class NotificationService:
    def __init__(self, db: DatabaseService):
        """Initialize the notification service.
        
        Args:
            db (DatabaseService): Database service instance
        """
        self.db = db
        self._notify_message_id = None
        self._notification_message = None

    @property
    def notify_message_id(self):
        """Get the notification message ID."""
        return self._notify_message_id

    @notify_message_id.setter
    def notify_message_id(self, value):
        """Set the notification message ID."""
        self._notify_message_id = value

    async def handle_reaction_add(self, channel, user_id, message_id, emoji):
        """Handle when a reaction is added to a message.
        
        Args:
            channel: Discord channel object
            user_id (int): ID of the user who added the reaction
            message_id (int): ID of the message that was reacted to
            emoji (str): The emoji that was added
        """
        try:
            message = await channel.fetch_message(message_id)
            if "Geburtstags-Benachrichtigungen" in message.content and str(emoji) == "✅":
                logger.info(f"User {user_id} enabled DM notifications")
                # Update DM preference (user should already exist from startup sync)
                self.db.update_dm_preference(user_id, True)
                logger.info(f"DM preference enabled for user {user_id}")
        except Exception as e:
            logger.error(f"Error handling reaction add: {e}")

    async def handle_reaction_remove(self, channel, user_id, message_id, emoji):
        """Handle when a reaction is removed from a message.
        
        Args:
            channel: Discord channel object
            user_id (int): ID of the user who removed the reaction
            message_id (int): ID of the message that was unreacted to
            emoji (str): The emoji that was removed
        """
        try:
            message = await channel.fetch_message(message_id)
            if "Geburtstags-Benachrichtigungen" in message.content and str(emoji) == "✅":
                logger.info(f"User {user_id} disabled DM notifications")
                self.db.update_dm_preference(user_id, False)
        except Exception as e:
            logger.error(f"Error handling reaction remove: {e}")

    async def setup_notification_message(self, channel: discord.TextChannel) -> bool:
        """Set up notification message in the given channel.
        
        Args:
            channel: The Discord text channel to set up notifications in.
            
        Returns:
            bool: True if setup was successful, False otherwise.
        """
        try:
            # Search for existing notification message
            async for message in channel.history(limit=100):
                if "Geburtstags-Benachrichtigungen" in message.content:
                    self._notification_message = message
                    self._notify_message_id = message.id
                    logger.info(f"Found existing notification message with ID: {message.id}")
                    return True

            # If no existing message found, create a new one
            message_content = "Reagiere mit ✅ um Geburtstags-Benachrichtigungen zu erhalten!"
            self._notification_message = await channel.send(message_content)
            await self._notification_message.add_reaction("✅")
            self._notify_message_id = self._notification_message.id
            logger.info(f"Created new notification message with ID: {self._notification_message.id}")
            
            return True
        except Exception as e:
            logger.error(f"Error setting up notification message: {str(e)}")
            return False

    async def send_test_dms_to_all(self, guild: discord.Guild) -> tuple[int, int]:
        """Send test DMs to all users with DM preferences enabled.
        
        Args:
            guild: The Discord guild to get members from
            
        Returns:
            tuple[int, int]: (success_count, failure_count)
        """
        success_count = 0
        failure_count = 0
        
        # Get all users with DM preferences enabled
        users_with_dm = self.db.get_users_with_dm_enabled()
        
        for user_id, in users_with_dm:
            try:
                # Try to get the user directly first
                try:
                    user = await guild.fetch_member(user_id)
                except discord.NotFound:
                    logger.warning(f"User {user_id} not found in guild")
                    failure_count += 1
                    continue
                    
                if user:
                    try:
                        await user.send("🎉 Dies ist eine Test-DM vom Birthday Bot! 🎂\n"
                                      "Du erhältst diese Nachricht, weil du dich für Geburtstags-Benachrichtigungen angemeldet hast.")
                        success_count += 1
                        logger.info(f"Sent test DM to user {user.name} (ID: {user_id})")
                    except discord.Forbidden:
                        logger.warning(f"Could not send DM to user {user.name} (ID: {user_id}): User has DMs disabled")
                        failure_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send test DM to user {user.name} (ID: {user_id}): {e}")
                        failure_count += 1
                else:
                    logger.warning(f"Could not find member with ID {user_id} in guild")
                    failure_count += 1
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                failure_count += 1
                
        return success_count, failure_count

    async def test_dm(self, user):
        """Test DM functionality for a user.
        
        Args:
            user: Discord user object to test DM with
            
        Returns:
            bool: True if DM was sent successfully, False otherwise
        """
        try:
            await user.send("🎉 Dies ist eine Test-DM vom Birthday Bot! 🎂")
            return True
        except Exception as e:
            logger.error(f"Failed to send test DM to user {user.id}: {e}")
            return False