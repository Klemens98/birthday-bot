"""Tests for the message utility functions."""
from utils.message_utils import (
    format_birthday_message,
    format_upcoming_birthdays,
    format_help_message
)
from datetime import datetime

def test_format_birthday_message():
    """Test birthday message formatting."""
    # Test with just display name
    msg = format_birthday_message("TestUser")
    assert msg == "🎉 Alles Gute zum Geburtstag, TestUser! 🎂"
    
    # Test with first and last name
    msg = format_birthday_message("TestUser", "John", "Doe")
    assert msg == "🎉 Alles Gute zum Geburtstag, TestUser (John Doe)! 🎂"
    
    # Test with first name only and different display name
    msg = format_birthday_message("John", "John", display_name="TestUser")
    assert msg == "🎉 Alles Gute zum Geburtstag, John! 🎂"
    
    # Test with different first name and display name
    msg = format_birthday_message("TestUser", "John", display_name="TestUser")
    assert msg == "🎉 Alles Gute zum Geburtstag, TestUser (John)! 🎂"

def test_format_upcoming_birthdays():
    """Test upcoming birthdays message formatting."""
    # Test with no birthdays
    msg = format_upcoming_birthdays([])
    assert msg == "Keine anstehenden Geburtstage gefunden."
    
    # Test with one birthday
    birthdays = [(
        123456789,  # user_id
        "testuser",  # username
        "John",      # firstname
        "Doe",       # lastname
        datetime(2023, 12, 1),  # birthday
        False        # dm_enabled
    )]
    msg = format_upcoming_birthdays(birthdays)
    assert "John Doe: 01.12." in msg
    assert "**Anstehende Geburtstage:**" in msg
    
    # Test with multiple birthdays
    birthdays.append((
        987654321,
        "testuser2",
        None,
        None,
        datetime(2023, 12, 15),
        False
    ))
    msg = format_upcoming_birthdays(birthdays)
    assert "John Doe: 01.12." in msg
    assert "testuser2: 15.12." in msg
    assert msg.count("\n") == 3  # Header + 2 birthdays

def test_format_help_message():
    """Test help message formatting."""
    # Test regular user help
    msg = format_help_message(is_admin=False)
    assert "Birthday Bot Befehle" in msg
    assert "Admin Befehle" not in msg
    assert "/help" in msg
    assert "/setbirthday" in msg
    assert "/birthdaycheck" not in msg
    
    # Test admin help
    msg = format_help_message(is_admin=True)
    assert "Birthday Bot Befehle" in msg
    assert "Admin Befehle" in msg
    assert "/help" in msg
    assert "/setbirthday" in msg
    assert "/birthdaycheck" in msg
    assert "/setupnotify" in msg