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

    async def sync_dm_preferences_from_reactions(self, guild) -> None:
        """Sync DM preferences based on current reactions on the notification message.
        
        This method checks the reactions on the notification message and updates
        the database to match the current state of reactions, useful for catching
        changes that happened while the bot was offline.
        
        Args:
            guild: Discord guild object
        """
        try:
            if not self._notification_message:
                logger.warning("No notification message found, skipping DM preference sync")
                return
                
            # Refresh the message to get current reactions
            channel = self._notification_message.channel
            message = await channel.fetch_message(self._notification_message.id)
            
            # Find the ✅ reaction
            checkmark_reaction = None
            for reaction in message.reactions:
                if str(reaction.emoji) == "✅":
                    checkmark_reaction = reaction
                    break
            
            if not checkmark_reaction:
                logger.info("No ✅ reaction found on notification message")
                return
                
            # Get all users who reacted with ✅
            reacted_user_ids = set()
            async for user in checkmark_reaction.users():
                if not user.bot:  # Exclude bot users
                    reacted_user_ids.add(user.id)
            
            logger.info(f"Found {len(reacted_user_ids)} users with ✅ reactions")
            
            # Get all guild member IDs to validate
            guild_member_ids = {member.id for member in guild.members}
            
            # Filter to only include current guild members
            valid_reacted_users = reacted_user_ids.intersection(guild_member_ids)
            
            # Get current DM preferences from database
            current_dm_users = set()
            dm_enabled_users = self.db.get_users_with_dm_enabled()
            for user_tuple in dm_enabled_users:
                current_dm_users.add(user_tuple[0])  # Extract user_id from tuple
            
            # Users who have reactions but DM disabled in DB
            to_enable = valid_reacted_users - current_dm_users
            
            # Users who have DM enabled in DB but no reaction (among guild members)
            to_disable = current_dm_users.intersection(guild_member_ids) - valid_reacted_users
            
            # Update database
            updates_made = 0
            for user_id in to_enable:
                self.db.update_dm_preference(user_id, True)
                logger.info(f"Enabled DM preference for user {user_id} based on reaction")
                updates_made += 1
                
            for user_id in to_disable:
                self.db.update_dm_preference(user_id, False)
                logger.info(f"Disabled DM preference for user {user_id} (no reaction found)")
                updates_made += 1
            
            logger.info(f"DM preference sync complete: {updates_made} updates made")
            
        except Exception as e:
            logger.error(f"Error syncing DM preferences from reactions: {e}")

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