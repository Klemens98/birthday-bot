# Birthday Bot

A Discord bot that manages and announces birthdays, with support for DM notifications and multiple users.

## Project Structure

```
birthday-bot/
├── services/           # Core business logic
│   ├── birthday_service.py    # Birthday processing logic
│   └── notification_service.py # Notification handling
├── handlers/           # Discord event and command handlers
│   ├── command_handler.py     # Slash command handling
│   └── event_handler.py       # Discord event handling
├── utils/             # Utility functions
│   ├── date_utils.py         # Date manipulation utilities
│   └── message_utils.py      # Message formatting utilities
├── config/            # Configuration management
│   └── config_manager.py     # Config loading and access
├── tests/             # Test modules
│   ├── conftest.py           # Test configuration
│   ├── test_birthday_service.py
│   ├── test_notification_service.py
│   ├── test_config_manager.py
│   ├── test_date_utils.py
│   └── test_message_utils.py
├── database.py        # Database operations
├── birthday_bot.py    # Main bot implementation
├── config.yaml        # Bot configuration
├── requirements.txt   # Production dependencies
└── dev-requirements.txt # Development dependencies
```

## Features

- Birthday tracking and announcements
- DM notifications for birthdays
- Slash command interface
- Timezone support (default: Europe/Berlin)
- First and last name support
- Admin commands for manual checks

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `config.yaml`:
```yaml
DISCORD:
  TOKEN: "your-bot-token"
  APPLICATION_ID: "your-app-id"
  CHANNEL_ID: "your-channel-id"
TIMEZONE: "Europe/Berlin"
```

4. Run the bot:
```bash
python birthday_bot.py
```

## Development Setup

1. Install development dependencies:
```bash
pip install -r dev-requirements.txt
```

2. Set up pre-commit hooks:
```bash
pre-commit install
```

3. Run tests:
```bash
pytest tests/
```

The project uses several code quality tools:
- Black for code formatting
- Flake8 for linting
- isort for import sorting
- pre-commit hooks for automated checks

## Commands

### User Commands
- `/help` - Display available commands
- `/setbirthday DD.MM.YYYY [firstname] [lastname]` - Set your birthday
- `/setbirthdayfor username DD.MM.YYYY [firstname] [lastname]` - Set someone's birthday
- `/nextbirthday [username]` - Show next birthday
- `/upcoming` - Show next 5 birthdays

### Admin Commands
- `/birthdaycheck` - Manual birthday check
- `/setupnotify` - Create notification opt-in message

## Development

### Testing
Run tests with pytest:
```bash
pytest tests/
```

### Continuous Integration
The project uses GitHub Actions for:
- Running tests on Python 3.9, 3.10, and 3.11
- Automated testing on push and pull requests
- Code quality checks

### Project Components

1. **Services**:
   - `BirthdayService`: Handles birthday processing and announcements
   - `NotificationService`: Manages DM notifications and preferences

2. **Handlers**:
   - `CommandHandler`: Processes slash commands
   - `EventHandler`: Handles Discord events

3. **Utilities**:
   - `date_utils.py`: Date manipulation functions
   - `message_utils.py`: Message formatting

4. **Configuration**:
   - `ConfigManager`: Loads and manages bot configuration

5. **Database**:
   - SQLite-based storage
   - Stores user birthdays and preferences

## License

MIT License
