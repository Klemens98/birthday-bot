"""Birthday service module for managing birthday-related operations."""
import logging
from datetime import datetime
import pytz
from database import DatabaseService

logger = logging.getLogger('BirthdayBot.BirthdayService')

class BirthdayService:
    def __init__(self, db: DatabaseService):
        """Initialize the birthday service.
        
        Args:
            db (DatabaseService): Database service instance
        """
        self.db = db

    async def process_todays_birthdays(self, guild, channel, bot_client):
        """Process and announce today's birthdays.
        
        Args:
            guild: Discord guild object
            channel: Discord channel object
            bot_client: Bot client object (to fetch users for DMs)
        
        Returns:
            list: List of processed birthday messages
        """
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        birthdays = self.db.get_todays_birthdays()
        
        if not birthdays:
            logger.info("No birthdays found for today")
            return []

        notif_users = self.db.get_users_with_dm_enabled()
        birthday_messages = []

        for user_id, username, firstname, lastname, birthday, dm_preference in birthdays:
            logger.info(f"Processing birthday for {username} (ID: {user_id})")
            member = guild.get_member(user_id)
            display_name = member.display_name if member else username
            
            if member and display_name != username:
                # Only update the username, keep the original birthday
                self.db.update_username(user_id, display_name)
            
            name_to_use = firstname or display_name
            message = self._construct_birthday_message(name_to_use, firstname, lastname, display_name)
            birthday_messages.append(message)
            
            await self._send_notifications(channel, message, user_id, name_to_use, notif_users, bot_client)

        return birthday_messages

    def _construct_birthday_message(self, name_to_use, firstname, lastname, display_name):
        """Construct the birthday message.
        
        Args:
            name_to_use (str): Primary name to use in message
            firstname (str): First name if available
            lastname (str): Last name if available
            display_name (str): Discord display name
            
        Returns:
            str: Formatted birthday message
        """
        message = f"🎉 Alles Gute zum Geburtstag, {name_to_use}"
        if firstname and lastname:
            message += f" ({firstname} {lastname})"
        elif firstname and display_name != firstname:
            message += f" ({display_name})"
        message += "! 🎂"
        return message

    async def _send_notifications(self, channel, message, birthday_user_id, name_to_use, notif_users, bot_client):
        """Send birthday notifications to channel and DMs.
        
        Args:
            channel: Discord channel object
            message (str): Birthday message to send
            birthday_user_id (int): ID of user having birthday
            name_to_use (str): Name to use in notifications
            notif_users (list): List of users to notify
            bot_client: Bot client object (to fetch users)
        """
        await channel.send(message)
        
        for notif_user_id, *_ in notif_users:
            try:
                notif_user = await bot_client.fetch_user(notif_user_id)
                if notif_user:
                    if notif_user_id == birthday_user_id:
                        # Send birthday greeting to the birthday person
                        await notif_user.send(f"🎉 Alles Gute zum Geburtstag! Ich hoffe, du hast einen wunderschönen Tag! 🎂")
                        logger.info(f"Sent birthday greeting to birthday user {notif_user_id}")
                    else:
                        # Send notification to others about the birthday
                        await notif_user.send(f"🎂 {name_to_use} hat heute Geburtstag!")
                        logger.info(f"Sent birthday notification to user {notif_user_id}")
            except Exception as e:
                logger.error(f"Failed to send DM to user {notif_user_id}: {e}")