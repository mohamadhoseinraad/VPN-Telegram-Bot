# VPN Telegram Bot

A full-featured Telegram bot for managing VPN services through an XUI panel.

## Overview

This Telegram bot provides a user-friendly interface for managing VPN services. It allows users to create VPN accounts, manage their configurations, check usage statistics, request support, and make payments. Administrators can manage clients, respond to support tickets, and approve payment requests.

## Features

- **User Management**: Create and manage VPN user accounts
- **VPN Configuration**: Generate, activate, and deactivate VPN configurations
- **Free Trial System**: Offer limited-time free trials to new users
- **Subscription Plans**: Various subscription plans with different durations and data limits
- **Payment Integration**: Process and verify payment requests
- **Support Ticketing**: In-bot support ticket system for user assistance
- **Admin Controls**: Comprehensive admin panel for managing users and configurations
- **Notification Service**: Automated notifications for expiring accounts and other important events
- **Usage Statistics**: Track and display user bandwidth usage

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install python-telegram-bot requests
   ```
3. Configure the settings in `config.py`

## Configuration

Edit the `config.py` file to set up your environment:

- `ADMIN_IDS`: List of Telegram user IDs with admin privileges
- `BOT_TOKEN`: Your Telegram bot token from BotFather
- `XUI_URL`: URL of your XUI panel
- `XUI_USERNAME`: XUI panel username
- `XUI_PASSWORD`: XUI panel password
- `INBOUND_ID`: XUI panel inbound ID
- `IPDOMAIN`: Server IP or domain
- `DOMAIN`: Your service domain
- `PORT`: Service port
- `HOST` & `SNI`: Additional connection settings if needed
- `DB_FILE`: Database filename
- `ALLOW_BUY`: Toggle to enable/disable purchase functionality

## Project Structure

- `bot.py`: Main bot application and command handlers
- `client_management.py`: Functions for managing VPN clients
- `config.py`: Configuration settings
- `database.py`: Database operations and schema
- `db_utils.py`: Database utility functions
- `menus.py`: Telegram inline keyboard menus
- `notification_service.py`: Automated notification system
- `xui_api.py`: API interactions with the XUI panel

## Usage

1. Start the bot:
   ```
   python bot.py
   ```

2. Access the bot on Telegram and use the available commands:
   - `/start` - Initialize the bot
   - `/help` - Show help information
   - Additional commands as configured in the bot

## Admin Commands

Administrators have access to additional commands and functionality:
- Manage user accounts
- Process payment requests
- Respond to support tickets
- View system statistics
- Extend client subscriptions

## Security

- Access to admin functions is restricted to users with IDs listed in the `ADMIN_IDS` setting
- User data is stored in a local SQLite database

## Dependencies

- python-telegram-bot
- requests
- sqlite3 (built-in)

## License

This project is proprietary software. All rights reserved.

## Support

For support inquiries, contact the administrator through the bot's ticket system or directly through Telegram.
