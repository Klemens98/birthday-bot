"""Main bot module that initializes and runs the Discord bot."""
import os
import sys
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import discord
from discord import app_commands
from discord.ext import tasks
import logging
import pytz
from datetime import time

from database import DatabaseService
from services.birthday_service import BirthdayService
from services.notification_service import NotificationService
from handlers.command_handler import CommandHandler
from handlers.event_handler import EventHandler
from config.config_manager import ConfigManager
from utils.date_utils import get_berlin_now

NOTIFICATION_MESSAGE = "Reagiere mit ✅ um Geburtstags-Benachrichtigungen zu erhalten!"
NOTIFICATION_EMOJI = "✅"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler('birthday_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BirthdayBot')

class BirthdayBot(discord.Client):
    def __init__(self):
        """Initialize the Birthday Bot with all necessary services and handlers."""
        logger.info("Initializing BirthdayBot")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.dm_messages = True
        intents.reactions = True

        try:
            self.config = ConfigManager()
            super().__init__(intents=intents, application_id=self.config.application_id)
            self.tree = app_commands.CommandTree(self)
            self.db = DatabaseService()
            self._setup_services()
            logger.info("BirthdayBot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BirthdayBot: {e}")
            raise

    def _setup_services(self):
        """Set up all services and handlers."""
        try:
            self.birthday_service = BirthdayService(self.db)
            self.notification_service = NotificationService(self.db)
            self.event_handler = EventHandler(self.notification_service, self.birthday_service)
            self.command_handler = CommandHandler(self.tree, self.db, 
                                              self.birthday_service, self.notification_service)
        except Exception as e:
            logger.error(f"Failed to setup services: {e}")
            raise

    async def setup_hook(self):
        """Set up the bot's background tasks and command tree."""
        try:
            self.check_birthdays.start()
            # Sync commands globally
            await self.tree.sync()
            # Also sync with the specific guild
            guild = discord.Object(id=self.config.guild_id)
            await self.tree.sync(guild=guild)
            logger.info(f"Command tree synced successfully for guild {self.config.guild_id}")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            raise

    async def on_ready(self):
        """Handle bot ready event."""
        logger.info(f"Bot is ready and logged in as {self.user}")
        try:
            # Update all usernames with current display names
            await self._update_all_usernames()
            
            birthday_channel = self.get_channel(self.config.channel_id)
            if not birthday_channel or not isinstance(birthday_channel, discord.TextChannel):
                raise ValueError(f"Invalid birthday channel configuration. Channel ID: {self.config.channel_id}")

            setup_result = await self.notification_service.setup_notification_message(birthday_channel)
            
            if not isinstance(setup_result, bool):
                raise TypeError(f"Expected bool from setup_notification_message, got {type(setup_result)}")
                
            if setup_result:
                logger.info(f"Successfully set up notifications in channel: {birthday_channel.name}")
                
                # Sync DM preferences based on current reactions
                guild = self.get_guild(self.config.guild_id)
                if guild:
                    await self.notification_service.sync_dm_preferences_from_reactions(guild)
                else:
                    logger.error(f"Could not find guild {self.config.guild_id} for DM preference sync")
            else:
                logger.error("Notification setup returned False")
        except Exception as e:
            logger.error(f"Error during startup: {e}")
            
    async def _update_all_usernames(self):
        """Update all stored usernames with their current display names and add new users."""
        try:
            # Get the guild
            guild = self.get_guild(self.config.guild_id)
            if not guild:
                logger.error(f"Could not find guild with ID {self.config.guild_id}")
                return
                
            # Get all current members in the guild
            current_members = {member.id: member for member in guild.members}
            logger.info(f"Found {len(current_members)} members in guild")
            
            # Get all users from the database
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT user_id, username FROM {self.db.table_name}")
                    db_users = {row[0]: row[1] for row in cur.fetchall()}
            
            logger.info(f"Found {len(db_users)} users in database")
            updated_count = 0
            added_count = 0
            
            # Update existing users and add new ones
            for member_id, member in current_members.items():
                try:
                    if member_id in db_users:
                        # Update existing user's display name if changed
                        if member.display_name != db_users[member_id]:
                            self.db.update_username(member_id, member.display_name)
                            updated_count += 1
                            logger.info(f"Updated username for user {member_id} from {db_users[member_id]} to {member.display_name}")
                    else:
                        # Add new user to database with NULL birthday
                        with self.db._get_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute(f"""
                                    INSERT INTO {self.db.table_name} 
                                        (user_id, username, birthday, firstname, lastname, dm_preference)
                                    VALUES (%s, %s, NULL, NULL, NULL, FALSE)
                                """, (member_id, member.display_name))
                                conn.commit()
                        added_count += 1
                        logger.info(f"Added new user {member.display_name} (ID: {member_id}) to database with NULL birthday")
                except Exception as e:
                    logger.error(f"Error processing member {member_id}: {e}")
            
            logger.info(f"Updated {updated_count} usernames and added {added_count} new users on startup")
        except Exception as e:
            logger.error(f"Error in _update_all_usernames: {e}")

    async def on_raw_reaction_add(self, payload):
        """Handle reaction add event."""
        try:
            channel = self.get_channel(payload.channel_id)
            if channel:
                await self.event_handler.on_raw_reaction_add(payload, channel, self.user)
            else:
                logger.error(f"Could not find channel with ID: {payload.channel_id}")
        except Exception as e:
            logger.error(f"Error handling reaction add: {str(e)}")

    async def on_raw_reaction_remove(self, payload):
        """Handle reaction remove event."""
        try:
            channel = self.get_channel(payload.channel_id)
            if channel:
                await self.event_handler.on_raw_reaction_remove(payload, channel, self.user)
            else:
                logger.error(f"Could not find channel with ID: {payload.channel_id}")
        except Exception as e:
            logger.error(f"Error handling reaction remove: {str(e)}")

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=pytz.timezone('Europe/Berlin')))
    async def check_birthdays(self):
        """Check and announce birthdays daily at midnight Berlin time."""
        try:
            now = get_berlin_now()
            logger.info(f"🎂 BIRTHDAY CHECK STARTED - Berlin time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            logger.info(f"🔍 Timezone fix active - checking birthdays for Berlin date: {now.strftime('%B %d, %Y')}")
            
            channel = self.get_channel(self.config.channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                birthday_messages = await self.birthday_service.process_todays_birthdays(
                    channel.guild, channel, self)
                
                if birthday_messages:
                    logger.info(f"✅ BIRTHDAY CHECK SUCCESS - Found and processed {len(birthday_messages)} birthday(s)")
                    for i, message in enumerate(birthday_messages, 1):
                        logger.info(f"   🎉 Birthday #{i}: {message}")
                else:
                    logger.info(f"ℹ️  BIRTHDAY CHECK COMPLETE - No birthdays found for {now.strftime('%B %d, %Y')} (Berlin time)")
            else:
                logger.error(f"Could not find valid birthday channel with ID: {self.config.channel_id}")
        except Exception as e:
            logger.error(f"❌ ERROR during birthday check: {str(e)}")

def main():
    """Main entry point for the bot."""
    bot = BirthdayBot()
    config = ConfigManager()
    bot.run(config.discord_token)

if __name__ == "__main__":
    main()