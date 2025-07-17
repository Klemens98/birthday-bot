"""Message utility functions for formatting bot messages."""

def format_birthday_message(name_to_use: str, firstname: str = None, 
                          lastname: str = None, display_name: str = None) -> str:
    """Format a birthday message for a user.
    
    Args:
        name_to_use (str): Primary name to use in message
        firstname (str, optional): User's first name
        lastname (str, optional): User's last name
        display_name (str, optional): Discord display name
        
    Returns:
        str: Formatted birthday message
    """
    message = f"🎉 Alles Gute zum Geburtstag, {name_to_use}"
    if firstname and lastname and name_to_use != f"{firstname} {lastname}":
        message += f" ({firstname} {lastname})"
    elif firstname and display_name and firstname != name_to_use and firstname != display_name:
        message += f" ({firstname})"
    message += "! 🎂"
    return message

def format_upcoming_birthdays(birthdays: list) -> str:
    """Format a list of upcoming birthdays.
    
    Args:
        birthdays (list): List of birthday tuples (user_id, username, firstname, 
                         lastname, birthday, dm_enabled)
        
    Returns:
        str: Formatted message with upcoming birthdays
    """
    if not birthdays:
        return "Keine anstehenden Geburtstage gefunden."
        
    message = "📅 **Anstehende Geburtstage:**\n"
    for _, username, firstname, lastname, birthday, _ in birthdays:
        name = firstname or username
        if firstname and lastname:
            name = f"{firstname} {lastname}"
        birthday_date = birthday.strftime('%d.%m.')
        message += f"• {name}: {birthday_date}\n"
    
    return message

def format_help_message(is_admin: bool = False) -> str:
    """Format the help message with available commands.
    
    Args:
        is_admin (bool): Whether to include admin commands
        
    Returns:
        str: Formatted help message
    """
    help_text = """**🎂 Birthday Bot Befehle:**
    /help - Zeigt diese Hilfe an
    /setbirthday DD.MM.YYYY [firstname] [lastname] - Setzt deinen Geburtstag
    /setbirthdayfor username DD.MM.YYYY [firstname] [lastname] - Setzt einen Geburtstag
    /nextbirthday [username] - Zeigt den nächsten Geburtstag
    /upcoming - Zeigt die nächsten 5 anstehenden Geburtstage

    ℹ️ Reagiere mit ✅ auf die Benachrichtigungsnachricht für DM-Benachrichtigungen.
    """
    
    if is_admin:
        help_text += """\n**Admin Befehle:**
    /birthdaycheck - Manuelle Geburtstagsüberprüfung
    /setupnotify - Erstellt die Benachrichtigungs-Nachricht
    """
    
    return help_text