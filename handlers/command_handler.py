"""Command handler module for managing Discord slash commands."""
import logging
from datetime import datetime
from typing import Optional
from discord import app_commands
import discord
from thefuzz import fuzz
from database import DatabaseService
from services.birthday_service import BirthdayService
from services.notification_service import NotificationService
from utils.message_utils import format_upcoming_birthdays

logger = logging.getLogger('BirthdayBot.CommandHandler')

class CommandHandler:
    def __init__(self, tree: app_commands.CommandTree, db: DatabaseService, 
                 birthday_service: BirthdayService, notification_service: NotificationService):
        """Initialize command handler.
        
        Args:
            tree: Discord command tree
            db: Database service instance
            birthday_service: Birthday service instance
            notification_service: Notification service instance
        """
        self.tree = tree
        self.db = db
        self.birthday_service = birthday_service
        self.notification_service = notification_service
        self._setup_commands()

    def _setup_commands(self):
        """Set up all slash commands."""
        
        @self.tree.command(name="help", description="Zeigt die Hilfe an")
        async def help(interaction: discord.Interaction):
            """Show help information."""
            logger.info(f"Help command used by {interaction.user.name}")
            help_text = (
                "**Geburtstags-Bot Hilfe**\n\n"
                "**Befehle:**\n"
                "`/setbirthday` - Setze deinen Geburtstag (Format: DD.MM.YYYY)\n"
                "`/upcoming` - Zeige die nächsten 5 anstehenden Geburtstage\n"
                "`/help` - Zeige diese Hilfe an\n\n"
                "**Wie funktioniert's?**\n"
                "1. Reagiere mit ✅ auf die Nachricht im Geburtstags-Kanal um Benachrichtigungen zu erhalten\n"
                "2. Setze deinen Geburtstag mit `/setbirthday`\n"
                "3. Erhalte Benachrichtigungen wenn jemand Geburtstag hat!\n"
                "4. Nutze `/upcoming` um zu sehen, wer als nächstes Geburtstag hat\n\n"
                "**Hinweis:** Benachrichtigungen werden nur an Benutzer gesendet, die mit ✅ reagiert haben."
            )
            await interaction.response.send_message(help_text, ephemeral=True)

        @self.tree.command(name="setbirthday", description="Setzt deinen Geburtstag (Format: DD.MM.YYYY)")
        @app_commands.describe(
            date="Dein Geburtsdatum im Format DD.MM.YYYY",
            firstname="Optional: Dein Vorname",
            lastname="Optional: Dein Nachname"
        )
        async def setbirthday(interaction: discord.Interaction, date: str, 
                            firstname: Optional[str] = None, lastname: Optional[str] = None):
            """Set a user's birthday."""
            logger.info(f"Setbirthday command used by {interaction.user.name}")
            try:
                # Validate date format
                try:
                    day, month, year = map(int, date.split('.'))
                    if not (1 <= day <= 31 and 1 <= month <= 12):
                        await interaction.response.send_message(
                            "Ungültiges Datum! Bitte verwende das Format DD.MM.YYYY",
                            ephemeral=True
                        )
                        return
                except ValueError:
                    await interaction.response.send_message(
                        "Ungültiges Datum! Bitte verwende das Format DD.MM.YYYY",
                        ephemeral=True
                    )
                    return

                # Create datetime object for the birthday
                birthday = datetime(year, month, day)
                
                # Update database using set_birthday (which handles both insert and update)
                self.db.set_birthday(
                    user_id=interaction.user.id,
                    username=interaction.user.display_name,
                    birthday=birthday,
                    firstname=firstname,
                    lastname=lastname
                )

                await interaction.response.send_message(
                    f"Geburtstag erfolgreich gesetzt auf: {date}",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error in setbirthday command: {e}")
                await interaction.response.send_message(
                    "Ein Fehler ist aufgetreten. Bitte versuche es später erneut.",
                    ephemeral=True
                )

        @self.tree.command(name="birthdaycheck", description="Überprüft manuell die heutigen Geburtstage")
        @app_commands.default_permissions(administrator=True)
        async def birthdaycheck(interaction: discord.Interaction):
            """Manually check for today's birthdays."""
            logger.info(f"Birthdaycheck command used by {interaction.user.name}")
            
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:  # type: ignore
                await interaction.response.send_message(
                    "Du hast keine Berechtigung, diesen Befehl auszuführen!",
                    ephemeral=True
                )
                return
            
            # Defer the response since this might take a while
            await interaction.response.defer(ephemeral=True)
            
            try:
                channel = interaction.client.get_channel(interaction.client.config.channel_id)  # type: ignore
                if not channel:
                    await interaction.followup.send(
                        "Konnte den Geburtstags-Kanal nicht finden!",
                        ephemeral=True
                    )
                    return
                
                await interaction.client.birthday_service.process_todays_birthdays(  # type: ignore
                    interaction.guild, channel, interaction.client.user)
                
                await interaction.followup.send(
                    "Geburtstags-Check erfolgreich durchgeführt!",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error in birthdaycheck command: {e}")
                await interaction.followup.send(
                    "Ein Fehler ist beim Geburtstags-Check aufgetreten.",
                    ephemeral=True
                )

        @self.tree.command(name="testdmall", description="Sendet Test-DMs an alle Benutzer mit aktivierten DM-Benachrichtigungen")
        async def testdmall(interaction: discord.Interaction):
            """Send test DMs to all users with DM preferences enabled."""
            logger.info(f"testdmall command used by {interaction.user.name}")
            
            # Check if user has admin permissions or is server owner
            if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):  # type: ignore
                await interaction.response.send_message(
                    "Du hast keine Berechtigung, diesen Befehl auszuführen!",
                    ephemeral=True
                )
                return
            
            # Defer the response since this might take a while
            await interaction.response.defer(ephemeral=True)
            
            try:
                # Log which table we're using
                table_name = interaction.client.db.table_name  # type: ignore
                logger.info(f"Using table {table_name} for testdmall command")
                
                # Get users with DM enabled
                users_with_dm = interaction.client.db.get_users_with_dm_enabled()  # type: ignore
                logger.info(f"Found {len(users_with_dm)} users with DM enabled in table {table_name}")
                
                if not users_with_dm:
                    await interaction.followup.send(
                        f"Keine Benutzer mit aktivierten DM-Benachrichtigungen in der Tabelle {table_name} gefunden.",
                        ephemeral=True
                    )
                    return
                
                success_count, failure_count = await interaction.client.notification_service.send_test_dms_to_all(interaction.guild)  # type: ignore
                
                # Send summary message
                await interaction.followup.send(
                    f"Test-DMs wurden gesendet (Tabelle: {table_name})!\n"
                    f"✅ Erfolgreich: {success_count}\n"
                    f"❌ Fehlgeschlagen: {failure_count}",
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error in testdmall command: {e}")
                await interaction.followup.send(
                    "Ein Fehler ist beim Senden der Test-DMs aufgetreten.",
                    ephemeral=True
                )

        @self.tree.command(name="upcoming", description="Zeigt die nächsten 5 anstehenden Geburtstage")
        async def upcoming(interaction: discord.Interaction):
            """Show the next 5 upcoming birthdays."""
            logger.info(f"Upcoming command used by {interaction.user.name}")
            try:
                # Get upcoming birthdays from database
                upcoming_birthdays = self.db.get_upcoming_birthdays(5)
                
                # Format the message
                message = format_upcoming_birthdays(upcoming_birthdays)
                
                # Send response (ephemeral so only the user can see it)
                await interaction.response.send_message(message, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error in upcoming command: {e}")
                await interaction.response.send_message(
                    "Ein Fehler ist aufgetreten beim Abrufen der anstehenden Geburtstage.",
                    ephemeral=True
                )

        # Add more commands here as needed
        # The remaining commands will be implemented similarly