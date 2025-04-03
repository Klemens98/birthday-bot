import discord
from discord import app_commands
from discord.ext import tasks
import yaml
from datetime import datetime
import pytz
from database import DatabaseService
from thefuzz import fuzz

def load_config():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

class BirthdayBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.dm_messages = True
        intents.reactions = True  # Add reactions intent
        self.config = load_config()
        super().__init__(intents=intents, application_id=int(self.config['DISCORD']['APPLICATION_ID']))
        self.tree = app_commands.CommandTree(self)
        self.db = DatabaseService()

    async def setup_hook(self):
        self.check_birthdays.start()

    async def on_raw_reaction_add(self, payload):
        # Check if the reaction is to a message that contains the preference text
        if str(payload.emoji) == "✅" and payload.user_id != self.user.id:
            channel = self.get_channel(payload.channel_id)
            if not channel:
                return
                
            try:
                message = await channel.fetch_message(payload.message_id)
                if "Geburtstags-Benachrichtigungen" in message.content:
                    self.db.update_dm_preference(payload.user_id, True)
            except discord.NotFound:
                pass

    async def on_raw_reaction_remove(self, payload):
        # Check if the reaction is to a message that contains the preference text
        if str(payload.emoji) == "✅" and payload.user_id != self.user.id:
            channel = self.get_channel(payload.channel_id)
            if not channel:
                return
                
            try:
                message = await channel.fetch_message(payload.message_id)
                if "Geburtstags-Benachrichtigungen" in message.content:
                    self.db.update_dm_preference(payload.user_id, False)
            except discord.NotFound:
                pass

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
        except Exception as e:
            print(f'Failed to sync application commands: {e}')

    @tasks.loop(hours=24)
    async def check_birthdays(self):
        tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(tz)
        
        # Only check at 9:00 AM German time
        if now.hour == 9:
            channel = self.get_channel(int(self.config['DISCORD']['CHANNEL_ID']))
            if channel and isinstance(channel, discord.TextChannel):
                birthdays = self.db.get_todays_birthdays()
                guild = channel.guild
                for user_id, username, birthday, dm_preference in birthdays:
                    age = now.year - birthday.year
                    # Update display name if it has changed
                    member = guild.get_member(user_id)
                    display_name = member.display_name if member else username
                    if member and display_name != username:
                        self.db.add_birthday(user_id, display_name, birthday, dm_preference)
                    
                    message = f"🎉 Alles Gute zum {age}. Geburtstag, {display_name}! 🎂"
                    await channel.send(message)
                    # Try to send DM to birthday person if they opted in
                    if dm_preference:
                        try:
                            user = await self.fetch_user(user_id)
                            if user:
                                await user.send(f"🎂 Alles Gute zum {age}. Geburtstag! 🎉")
                        except discord.errors.Forbidden:
                            pass  # User has DMs disabled

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
        /setbirthday DD.MM.YYYY - Setzt deinen Geburtstag
        /nextbirthday [username] - Zeigt den nächsten Geburtstag oder sucht nach einem bestimmten Benutzer
        /upcoming - Zeigt die nächsten 5 anstehenden Geburtstage
        """
        
        # Add admin commands if user has admin permissions
        if isinstance(interaction.channel, discord.TextChannel) and interaction.user.guild_permissions.administrator:
            help_text += """\n**Admin Befehle:**
        /birthdaycheck - Überprüft manuell die heutigen Geburtstage und sendet Glückwünsche
        /createpreferences - Erstellt die Benachrichtigungseinstellungen (falls nicht vorhanden)
        """
            
        help_text += "\nBitte benutze das richtige Format für die Befehle!"
        await interaction.response.send_message(help_text)

    @bot.tree.command(name="setbirthday", description="Setzt deinen Geburtstag (Format: DD.MM.YYYY)")
    @app_commands.describe(date="Dein Geburtsdatum im Format DD.MM.YYYY")
    async def setbirthday(interaction: discord.Interaction, date: str):
        try:
            birthday = datetime.strptime(date, '%d.%m.%Y')
            # Get display name if in a guild, otherwise use the username
            display_name = (interaction.user.display_name 
                          if isinstance(interaction.channel, discord.TextChannel) 
                          else str(interaction.user))
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
                age = now.year - birthday.year
                if days_until > 0:  # Birthday is in the future
                    age += 1  # Add 1 to age since it's their next birthday
                
                if days_until == 0:
                    response_lines.append(f"🎉 **{username}** hat heute Geburtstag! ({age})")
                else:
                    response_lines.append(f"🎂 **{username}** wird in {days_until} Tagen {age} (am {birthday.strftime('%d.%m.')})")
            
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
            
        birthday_messages = []
        for user_id, username, birthday in birthdays:
            age = now.year - birthday.year
            # Update display name if it has changed
            member = guild.get_member(user_id)
            display_name = member.display_name if member else username
            if member and display_name != username:
                bot.db.add_birthday(user_id, display_name, birthday)
            
            message = f"🎉 Alles Gute zum Geburtstag, {display_name}! 🎂"
            birthday_messages.append(message)
            await channel.send(message)
        
        summary = f"Manuelle Geburtstagsüberprüfung abgeschlossen: {len(birthdays)} Geburtstage gefunden."
        await interaction.followup.send(summary, ephemeral=True)

    bot.run(load_config()['DISCORD']['TOKEN'])

if __name__ == "__main__":
    main()