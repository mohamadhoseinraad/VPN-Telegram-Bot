"""
Notification Service for VPN Bot
Handles checking configs and sending notifications to users
"""
import logging
import time
from datetime import datetime
import threading
import schedule

from telegram.ext import ApplicationBuilder
from telegram import Bot, InlineKeyboardMarkup

from config import BOT_TOKEN
from database import get_all_configs_with_users, update_notification_sent
from xui_api import get_client_status, ensure_authenticated
from menus import get_back_to_main_button

logger = logging.getLogger(__name__)

# Constants
TRAFFIC_THRESHOLD_PERCENTAGE = 90  # Notify when 90% of data is used
DAYS_THRESHOLD = 2  # Notify when 2 days or less remaining
CHECK_INTERVAL_HOURS = 1  # Check every hour

async def send_notification(bot, user_id, message):
    """Send a notification message to a user"""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=message, reply_markup = InlineKeyboardMarkup(get_back_to_main_button())
        )
        logger.info(f"Notification sent to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")
        return False

async def check_and_notify_expiring_configs(bot):
    """Check for configs near expiry or data limit and send notifications"""
    logger.info("Starting check for expiring configs")

    # Ensure we're authenticated with the XUI panel once at the beginning
    if not ensure_authenticated():
        logger.error("Failed to authenticate with XUI panel")
        return

    # Get all configs with user info
    configs = get_all_configs_with_users()

    for config in configs:
        config_id = config['config_id']
        user_id = config['user_id']
        email = config['email']
        last_notified = config['last_notified']

        # Skip if already notified in the last 24 hours
        if last_notified and (datetime.now() - datetime.strptime(last_notified, '%Y-%m-%d %H:%M:%S')).total_seconds() < 86400:
            continue

        # Get current status from XUI panel - no need to login again for each check
        status = get_client_status(email)
        if not status:
            logger.warning(f"Could not retrieve status for config {email}")
            continue

        notification_needed = False
        notification_message = "⚠️ **هشدار وضعیت سرویس VPN** ⚠️\n\n"

        # Check for traffic limit
        total_gb = status['total_gb']
        remaining_gb = status['remaining_gb']
        used_percentage = ((total_gb - remaining_gb) / total_gb) * 100 if total_gb > 0 else 0

        if used_percentage >= TRAFFIC_THRESHOLD_PERCENTAGE:
            notification_needed = True
            notification_message += f"🔄 سرویس شما با نام {email} به {used_percentage:.1f}% از حجم ترافیک ��ود رسیده است.\n"
            notification_message += f"حجم باقیمانده: {remaining_gb:.2f} GB\n\n"

        # Check for expiry date
        remaining_days = status['remaining_days']
        remaining_hours = status['remaining_hours']

        if remaining_days <= DAYS_THRESHOLD:
            notification_needed = True
            notification_message += f"⏰ سرویس شما با نام {email} تنها {status['remaining_time_display']} دیگر اعتبار دارد.\n"
            notification_message += f"تاریخ انقضا: {status['expiry_date']}\n\n"

        # Send notification if needed
        if notification_needed:
            notification_message += "برای تمدید سرویس یا خرید سرویس جدید، لطفا از منوی اصلی ربات استفاده کنید."
            success = await send_notification(bot, user_id, notification_message)

            if success:
                # Update notification timestamp
                update_notification_sent(config_id)

def run_scheduler():
    """Run the scheduler in a background thread"""
    bot = Bot(token=BOT_TOKEN)

    def job():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(check_and_notify_expiring_configs(bot))

    # Schedule the job
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute if there are scheduled tasks to run

def start_notification_service(app):
    """Start the notification service in a background thread"""
    # Run once at startup
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_and_notify_expiring_configs(app.bot))

    # Start scheduler thread
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    logger.info("Notification service started")
