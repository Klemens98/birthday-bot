import discord
from discord import app_commands
from discord.ext import tasks
import yaml
from datetime import datetime
import pytz
from database import DatabaseService
from thefuzz import fuzz
import logging

def load_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('birthday_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BirthdayBot')

class BirthdayBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.dm_messages = True
        intents.reactions = True  # Add reaction intents


        self.config = load_config()
        super().__init__(intents=intents, application_id=int(self.config['DISCORD']['APPLICATION_ID']))
        self.tree = app_commands.CommandTree(self)
        self.db = DatabaseService()
        self.notify_message_id = None

    async def setup_hook(self):
        self.check_birthdays.start()

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id:
            return
            
        channel = self.get_channel(payload.channel_id)
        if not channel:
            logger.warning(f"Could not find channel for reaction: {payload.channel_id}")
            return
            
        try:
            message = await channel.fetch_message(payload.message_id)
            if "Geburtstags-Benachrichtigungen" in message.content and str(payload.emoji) == "✅":
                logger.info(f"User {payload.user_id} enabled DM notifications")
                self.db.update_dm_preference(payload.user_id, True)
        except discord.NotFound:
            logger.error(f"Could not find message for reaction: {payload.message_id}")
        except Exception as e:
            logger.error(f"Error handling reaction add: {str(e)}")

    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.user.id:
            return
            
        channel = self.get_channel(payload.channel_id)
        if not channel:
            logger.warning(f"Could not find channel for reaction removal: {payload.channel_id}")
            return
            
        try:
            message = await channel.fetch_message(payload.message_id)
            if "Geburtstags-Benachrichtigungen" in message.content and str(payload.emoji) == "✅":
                logger.info(f"User {payload.user_id} disabled DM notifications")
                self.db.update_dm_preference(payload.user_id, False)
        except discord.NotFound:
            logger.error(f"Could not find message for reaction removal: {payload.message_id}")
        except Exception as e:
            logger.error(f"Error handling reaction remove: {str(e)}")

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        try:
            # Set commands to work in DMs and guilds
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            # Also sync globally
            await self.tree.sync()
            print(f'Successfully synced application commands')

            # Check DM preferences on startup
            for guild in self.guilds:
                for channel in guild.text_channels:
                    try:
                        async for message in channel.history(limit=100):
                            if message.author == self.user and "Geburtstags-Benachrichtigungen" in message.content:
                                for reaction in message.reactions:
                                    if str(reaction.emoji) == "✅":
                                        async for user in reaction.users():
                                            if user != self.user:
                                                self.db.update_dm_preference(user.id, True)
                                                logger.info(f"Updated DM preference for user {user.id} on startup")
                    except (discord.Forbidden, discord.HTTPException) as e:
                        logger.error(f"Error checking channel {channel.id}: {e}")

        except Exception as e:
            print(f'Failed to sync application commands or check DM preferences: {e}')

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        
        # Only check at midnight German time
        if now.hour == 0:
            channel = self.get_channel(int(self.config['DISCORD']['CHANNEL_ID']))
            if channel and isinstance(channel, discord.TextChannel):
                birthdays = self.db.get_todays_birthdays()
                guild = channel.guild


                # Get all users who want notifications
                notif_users = self.db.get_users_with_dm_enabled()
                
                for user_id, username, birthday in birthdays:

                    # Update display name if it has changed
                    member = guild.get_member(user_id)
                    display_name = member.display_name if member else username
                    if member and display_name != username:
                        self.db.add_birthday(user_id, display_name, birthday, dm_preference)
                    
                    # Extract firstname if available
                    firstname = username.split()[0] if ' ' in username else None
                    name_to_use = firstname or display_name
                    
                    # Construct message without age
                    message = f"🎉 Alles Gute zum Geburtstag, {name_to_use}"
                    if firstname and display_name != username:
                        message += f" ({display_name})"
                    message += "! 🎂"
                    
                    # Only send message in channel
                    await channel.send(message)
                    
                    # Notify opted-in users about the birthday
                    for notif_user_id, _, _ in notif_users:
                        if notif_user_id != user_id:  # Don't notify the birthday person
                            try:
                                notif_user = await self.fetch_user(notif_user_id)
                                if notif_user:
                                    await notif_user.send(f"🎂 {name_to_use} hat heute Geburtstag!")
                            except (discord.errors.Forbidden, Exception):
                                pass  # User has DMs disabled or other errors


def main():
    bot = BirthdayBot()
    
    @bot.tree.command(name="createpreferences", description="Erstellt die Benachrichtigungseinstellungen (Admin)")
    @app_commands.default_permissions(administrator=True)
    async def create_preferences(interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Du hast keine Berechtigung, diesen Befehl auszuführen!", ephemeral=True)
            return

        # Get all messages in the channel
        messages = [msg async for msg in interaction.channel.history()]
        preference_exists = any("Geburtstags-Benachrichtigungen" in msg.content for msg in messages)

        if preference_exists:
            await interaction.response.send_message("Eine Benachrichtigungseinstellung existiert bereits in diesem Kanal!", ephemeral=True)
            return

        message = await interaction.channel.send(
            "🔔 **Geburtstags-Benachrichtigungen**\n\n"
            "Reagiere mit ✅ um private Geburtstagsnachrichten zu erhalten.\n"
            "Entferne deine Reaktion um die Benachrichtigungen zu deaktivieren."
        )
        await message.add_reaction("✅")
        await message.pin()
        await interaction.response.send_message("Benachrichtigungseinstellungen wurden erstellt!", ephemeral=True)

    @bot.tree.command(name="help", description="Zeigt die Hilfe an")
    async def help(interaction: discord.Interaction):
        help_text = """**🎂 Birthday Bot Befehle:**
        /help - Zeigt diese Hilfe an
        /setbirthday DD.MM.YYYY [firstname] [lastname] - Setzt deinen Geburtstag mit optionalem Vor- und Nachnamen
        /setbirthdayfor username DD.MM.YYYY [firstname] [lastname] - Setzt den Geburtstag für einen anderen Benutzer
        /nextbirthday [username] - Zeigt den nächsten Geburtstag oder sucht nach einem bestimmten Benutzer
        /upcoming - Zeigt die nächsten 5 anstehenden Geburtstage

        ℹ️ Um Geburtstags-Benachrichtigungen zu erhalten, reagiere mit ✅ auf die Benachrichtigungsnachricht im Geburtstags-Kanal.
        """
        
        # Add admin commands if user has admin permissions
        if isinstance(interaction.channel, discord.TextChannel) and interaction.user.guild_permissions.administrator:
            help_text += """\n**Admin Befehle:**
        /birthdaycheck - Überprüft manuell die heutigen Geburtstage und sendet Glückwünsche
        /setupnotify - Erstellt die Benachrichtigungs-Nachricht für Geburtstags-Benachrichtigungen

        """
            
        help_text += "\nBitte benutze das richtige Format für die Befehle!"
        await interaction.response.send_message(help_text)

    @bot.tree.command(name="setbirthday", description="Setzt deinen Geburtstag (Format: DD.MM.YYYY)")
    @app_commands.describe(
        date="Dein Geburtsdatum im Format DD.MM.YYYY",
        firstname="Optional: Dein Vorname",
        lastname="Optional: Dein Nachname"
    )
    async def setbirthday(
        interaction: discord.Interaction,
        date: str,
        firstname: str = None,
        lastname: str = None
    ):
        try:
            birthday = datetime.strptime(date, '%d.%m.%Y')
            # Get display name if in a guild, otherwise use the username
            base_name = (interaction.user.display_name 
                      if isinstance(interaction.channel, discord.TextChannel) 
                      else str(interaction.user))
            
            # Construct display name with optional first and last name
            if firstname or lastname:
                display_name = f"{firstname or ''} {lastname or ''}".strip()
            else:
                display_name = base_name
                
            bot.db.add_birthday(interaction.user.id, display_name, birthday)
            await interaction.response.send_message(f"Geburtstag für {display_name} wurde auf {date} gesetzt!")
        except ValueError:
            await interaction.response.send_message("Bitte gib das Datum im Format DD.MM.YYYY ein!")

    @bot.tree.command(name="nextbirthday", description="Zeigt den nächsten Geburtstag oder sucht nach einem Benutzer")
    @app_commands.describe(username="Optional: Nach diesem Benutzer suchen")
    async def nextbirthday(interaction: discord.Interaction, username: str = None):
        if username:
            results = bot.db.search_birthday_by_username('')  # Get all users for fuzzy matching
            if results:
                response_lines = []
                tz = pytz.timezone('Europe/Berlin')
                now = datetime.now(tz)
                
                # Update usernames with current display names if possible
                if isinstance(interaction.channel, discord.TextChannel):
                    guild = interaction.guild
                    for user_id, stored_name, birthday in results:
                        member = guild.get_member(user_id)
                        if member and member.display_name != stored_name:
                            bot.db.add_birthday(user_id, member.display_name, birthday)
                
                # Filter and sort results by fuzzy match ratio using multiple methods
                fuzzy_matches = []
                for user_id, found_username, birthday in results:
                    if birthday is None:  # Skip entries with no birthday
                        continue
                        
                    # Use multiple matching methods and take the best score
                    partial_score = fuzz.partial_ratio(username.lower(), found_username.lower())
                    token_sort_score = fuzz.token_sort_ratio(username.lower(), found_username.lower())
                    best_score = max(partial_score, token_sort_score)
                    
                    if best_score > 50:  # Basic threshold for any matches
                        fuzzy_matches.append((best_score, user_id, found_username, birthday))
                
                # Sort by match ratio, highest first
                fuzzy_matches.sort(reverse=True)
                
                if fuzzy_matches:
                    # If we have a high confidence match (>80), only show the best match
                    # Otherwise show up to 5 matches to let the user choose
                    matches_to_show = fuzzy_matches[:1] if fuzzy_matches[0][0] > 80 else fuzzy_matches[:5]
                    
                    for score, user_id, found_username, birthday in matches_to_show:
                        if birthday:
                            next_date = birthday.replace(year=now.year)
                            if next_date < now.date():
                                next_date = next_date.replace(year=now.year + 1)
                            response_lines.append(f"{found_username}: {next_date.strftime('%d.%m.%Y')}")
                    
                    if len(matches_to_show) > 1:
                        await interaction.response.send_message("Mehrere mögliche Übereinstimmungen gefunden:\n" + "\n".join(response_lines))
                    else:
                        await interaction.response.send_message("\n".join(response_lines))
                else:
                    await interaction.response.send_message(f"Keine ähnlichen Benutzer zu '{username}' gefunden!")
            else:
                await interaction.response.send_message("Keine Geburtstage in der Datenbank gefunden!")
        else:
            next_birthday = bot.db.get_next_birthday()
            if next_birthday and len(next_birthday) == 3:  # Check we have all required data
                user_id, username, birthday = next_birthday
                if birthday:  # Check birthday is not None
                    tz = pytz.timezone('Europe/Berlin')
                    now = datetime.now(tz)
                    next_date = birthday.replace(year=now.year)
                    if next_date < now.date():
                        next_date = next_date.replace(year=now.year + 1)
                    await interaction.response.send_message(f"Der nächste Geburtstag ist von {username} am {next_date.strftime('%d.%m.%Y')}")
                else:
                    await interaction.response.send_message("Keine gültigen Geburtstage in der Datenbank gefunden!")
            else:
                await interaction.response.send_message("Keine Geburtstage in der Datenbank gefunden!")

    @bot.tree.command(name="upcoming", description="Zeigt die nächsten 5 anstehenden Geburtstage")
    async def upcoming(interaction: discord.Interaction):
        upcoming_birthdays = bot.db.get_upcoming_birthdays(5)
        if upcoming_birthdays:
            tz = pytz.timezone('Europe/Berlin')
            now = datetime.now(tz)
            
            # Update display names if in a guild
            if isinstance(interaction.channel, discord.TextChannel):
                guild = interaction.guild
                for user_id, stored_name, birthday, days_until in upcoming_birthdays:
                    member = guild.get_member(user_id)
                    if member and member.display_name != stored_name:
                        bot.db.add_birthday(user_id, member.display_name, birthday)
            
            response_lines = ["**📅 Anstehende Geburtstage:**"]
            for user_id, username, birthday, days_until in upcoming_birthdays:
                if days_until == 0:
                    response_lines.append(f"🎉 **{username}** hat heute Geburtstag!")
                else:
                    response_lines.append(f"🎂 **{username}** hat in {days_until} Tagen Geburtstag (am {birthday.strftime('%d.%m.')})")
            
            await interaction.response.send_message("\n".join(response_lines))
        else:
            await interaction.response.send_message("Keine Geburtstage in der Datenbank gefunden!")

    @bot.tree.command(name="testdm", description="Testet die DM-Funktionalität")
    @app_commands.default_permissions(administrator=True)
    async def testdm(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Du hast keine Berechtigung, diesen Befehl auszuführen!", ephemeral=True)
            return

        # Check if user has opted in for DMs
        user_preference = bot.db.get_dm_preference(interaction.user.id)
        if not user_preference:
            await interaction.response.send_message("Du hast DM-Benachrichtigungen nicht aktiviert. Bitte reagiere mit ✅ auf die Benachrichtigungseinstellungen!", ephemeral=True)
            return

        try:
            await interaction.user.send("🎉 Dies ist eine Test-DM vom Birthday Bot! 🎂")
            await interaction.response.send_message("DM wurde erfolgreich gesendet!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Konnte keine DM senden. Überprüfe, ob du DMs von Server-Mitgliedern erlaubst!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ein Fehler ist aufgetreten: {str(e)}", ephemeral=True)

    @bot.tree.command(name="birthdaycheck", description="Überprüft manuell die heutigen Geburtstage")
    async def birthdaycheck(interaction: discord.Interaction):
        # Check if user has admin permissions
        if not isinstance(interaction.channel, discord.TextChannel) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Du hast keine Berechtigung, diesen Befehl auszuführen!", ephemeral=True)
            return
            
        await interaction.response.defer(thinking=True)
        
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        channel = interaction.channel
        guild = interaction.guild
        
        birthdays = bot.db.get_todays_birthdays()
        if not birthdays:
            await interaction.followup.send("Heute hat niemand Geburtstag!", ephemeral=True)
            return

        # Get all users who want notifications
        notif_users = bot.db.get_users_with_dm_enabled()
            
        birthday_messages = []
        for user_id, username, birthday in birthdays:
            # Update display name if it has changed
            member = guild.get_member(user_id)
            display_name = member.display_name if member else username
            if member and display_name != username:
                bot.db.add_birthday(user_id, display_name, birthday)
            
            # Extract firstname if available
            firstname = username.split()[0] if ' ' in username else None
            name_to_use = firstname or display_name
            
            # Construct message without age
            message = f"🎉 Alles Gute zum Geburtstag, {name_to_use}"
            if firstname and display_name != username:
                message += f" ({display_name})"
            message += "! 🎂"
            
            birthday_messages.append(message)
            await channel.send(message)

            # Notify opted-in users about the birthday
            for notif_user_id, _, _ in notif_users:
                if notif_user_id != user_id:  # Don't notify the birthday person
                    try:
                        notif_user = await bot.fetch_user(notif_user_id)
                        if notif_user:
                            await notif_user.send(f"🎂 {name_to_use} hat heute Geburtstag!")
                    except (discord.errors.Forbidden, Exception):
                        pass  # User has DMs disabled or other errors
        
        summary = f"Manuelle Geburtstagsüberprüfung abgeschlossen: {len(birthdays)} Geburtstage gefunden."
        await interaction.followup.send(summary, ephemeral=True)

    @bot.tree.command(name="setbirthdayfor", description="Setzt den Geburtstag für einen anderen Benutzer")
    @app_commands.describe(
        username="Der Discord-Name oder Anzeigename des Benutzers",
        date="Geburtsdatum im Format DD.MM.YYYY",
        firstname="Optional: Vorname",
        lastname="Optional: Nachname"
    )
    async def setbirthdayfor(
        interaction: discord.Interaction,
        username: str,
        date: str,
        firstname: str = None,
        lastname: str = None
    ):
        try:
            birthday = datetime.strptime(date, '%d.%m.%Y')
        except ValueError:
            await interaction.response.send_message("Bitte gib das Datum im Format DD.MM.YYYY ein!", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Dieser Befehl kann nur in einem Server-Kanal verwendet werden!", ephemeral=True)
            return

        guild = interaction.guild
        # Get all members for fuzzy matching
        members = guild.members
        best_match = None
        best_score = 0

        for member in members:
            # Try matching against both username and display name
            partial_score_username = fuzz.partial_ratio(username.lower(), member.name.lower())
            partial_score_display = fuzz.partial_ratio(username.lower(), member.display_name.lower())
            token_sort_score_username = fuzz.token_sort_ratio(username.lower(), member.name.lower())
            token_sort_score_display = fuzz.token_sort_ratio(username.lower(), member.display_name.lower())
            
            best_member_score = max(partial_score_username, partial_score_display, 
                                  token_sort_score_username, token_sort_score_display)
            
            if best_member_score > best_score:
                best_score = best_member_score
                best_match = member

        if best_match and best_score > 60:  # Threshold for accepting a match
            # Construct display name with optional first and last name
            if firstname or lastname:
                display_name = f"{firstname or ''} {lastname or ''}".strip()
            else:
                display_name = best_match.display_name

            bot.db.add_birthday(best_match.id, display_name, birthday)
            
            confirmation = f"Geburtstag für {display_name} wurde auf {date} gesetzt!"
            if best_score < 90:  # If match wasn't perfect, show the matched user for verification
                confirmation += f"\n(Gefundener Benutzer: {best_match.display_name})"
            
            await interaction.response.send_message(confirmation)
        else:
            await interaction.response.send_message(f"Konnte keinen passenden Benutzer zu '{username}' finden.", ephemeral=True)

    @bot.tree.command(name="setupnotify", description="Erstellt die Benachrichtigungs-Nachricht für Geburtstags-Benachrichtigungen")
    async def setupnotify(interaction: discord.Interaction):
        # Check if user has admin permissions
        if not isinstance(interaction.channel, discord.TextChannel) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Du hast keine Berechtigung, diesen Befehl auszuführen!", ephemeral=True)
            return

        channel = interaction.channel
        # Look for existing notification message
        async for message in channel.history(limit=100):
            if message.author == bot.user and "Reagiere mit ✅" in message.content:
                bot.notify_message_id = message.id
                await interaction.response.send_message("Eine bestehende Benachrichtigungs-Nachricht wurde gefunden!", ephemeral=True)
                return
        
        # If no message found, create one
        message = await channel.send("🔔 Reagiere mit ✅ um Geburtstags-Benachrichtigungen zu erhalten!")
        await message.add_reaction("✅")
        bot.notify_message_id = message.id
        await interaction.response.send_message("Die Benachrichtigungs-Nachricht wurde erfolgreich erstellt!", ephemeral=True)

    bot.run(load_config()['DISCORD']['TOKEN'])

if __name__ == "__main__":
    main()