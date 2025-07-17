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
        "testuser2",  # Use username as firstname when no first name is set
        "",           # Empty string instead of None
        datetime(2023, 12, 15),
        False
    ))
    msg = format_upcoming_birthdays(birthdays)
    assert "John Doe: 01.12." in msg
    assert "testuser2: 15.12." in msg
    assert msg.count("\n") == 3  # Header + 2 birthdays

def test_format_upcoming_birthdays_with_limit():
    """Test that upcoming birthdays formatting works with different numbers of birthdays."""
    # Test with exactly 5 birthdays
    birthdays = []
    for i in range(5):
        birthdays.append((
            i,  # user_id
            f"user{i}",  # username
            f"First{i}",  # firstname
            f"Last{i}",   # lastname
            datetime(2023, 12, i+1),  # birthday
            False  # dm_enabled
        ))
    
    msg = format_upcoming_birthdays(birthdays)
    assert msg.count("\n") == 6  # Header + 5 birthdays
    assert "First0 Last0: 01.12." in msg
    assert "First4 Last4: 05.12." in msg

def test_format_help_message():
    """Test help message formatting."""
    # Test regular user help
    help_msg = format_help_message()
    assert "/help" in help_msg
    assert "/setbirthday" in help_msg
    assert "/upcoming" in help_msg
    
    # Test admin help
    admin_help = format_help_message(is_admin=True)
    assert "/birthdaycheck" in admin_help
    assert "/setupnotify" in admin_help