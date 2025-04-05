# Discord Birthday Bot

A Discord bot that helps manage and celebrate birthdays in your server.

## Features

- Store and track server members' birthdays
- Send birthday announcements in designated channels
- Allow users to set and update their own birthdays
- View upcoming birthdays

## Setup

1. Clone the repository
2. Install dependencies:
```bash
npm install
```
3. Create a `config.yaml` file with your configuration:
```yaml
DISCORD:
  TOKEN: your_token_here
  CHANNEL_ID: your_channel_id_here  # Replace with your channel ID
  APPLICATION_ID: your_application_id_here

DATABASE:
  NAME: default
  HOST: localhost
  PORT: 5432
  USER: your_db_user
  PASSWORD: your_db_password
```
4. Start the bot:
```bash
npm start
```

## Commands

- `/setbirthday` - Set your birthday
- `/birthday` - View someone's birthday
- `/upcoming` - List upcoming birthdays
- `/settings` - Configure bot settings (Admin only)

## Contributing

Feel free to open issues or submit pull requests with improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
