"""
Client management functions for VPN Telegram Bot
"""
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config

logger = logging.getLogger(__name__)

async def show_all_clients(query, context, page=0, admin_ids=config.ADMIN_IDS):
    """Show all clients with pagination, combining XUI panel data and database data"""
    if admin_ids is None:
        admin_ids = []

    if query.from_user.id not in admin_ids:
        await query.answer("دسترسی رد شد.")
        return

    # Import functions to get clients from both sources
    from xui_api import get_all_clients
    from db_utils import get_all_db_configs

    # Get all clients from XUI panel
    xui_clients = get_all_clients() or []

    # Get all clients from database
    db_clients = get_all_db_configs() or []

    # Create a dictionary to store the merged clients, using client_id as key
    all_clients = {}

    # Process XUI clients first
    for client in xui_clients:
        client_id = client.get('id')
        if client_id:
            # Mark as existing in XUI
            client['in_xui'] = True
            all_clients[client_id] = client

    # Process database clients, adding or updating information
    for client in db_clients:
        client_id = client.get('client_id')
        if client_id:
            if client_id in all_clients:
                # Client exists in both places, update with database info
                all_clients[client_id].update({
                    'user_id': client.get('user_id'),
                    'username': client.get('username'),
                    'first_name': client.get('first_name'),
                    'db_total_gb': client.get('total_gb'),
                    'created_at': client.get('created_at'),
                    'in_db': True
                })
            else:
                # Client only exists in database
                all_clients[client_id] = {
                    'id': client_id,
                    'email': client.get('email'),
                    'total_gb': client.get('total_gb'),
                    'is_active': client.get('is_active', False),
                    'user_id': client.get('user_id'),
                    'username': client.get('username'),
                    'first_name': client.get('first_name'),
                    'created_at': client.get('created_at'),
                    'in_db': True,
                    'in_xui': False
                }

    # Convert dictionary back to list
    clients = list(all_clients.values())

    if not clients:
        await query.edit_message_text(
            "⚠️ هیچ کلاینتی یافت نشد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]])
        )
        return

    # Define a sorting key function that handles different timestamp formats
    def get_sort_key(client):
        # First try to get created_at timestamp
        created_at = client.get('created_at')
        if created_at:
            # Convert string timestamp to int if it's a string
            if isinstance(created_at, str):
                try:
                    # Try parsing ISO format timestamp
                    import time
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    return int(dt.timestamp())
                except (ValueError, TypeError):
                    # If parsing fails, return 0
                    return 0
            return created_at

        # Fall back to expiryTime
        expiry_time = client.get('expiryTime', 0)
        if isinstance(expiry_time, str):
            try:
                return int(expiry_time)
            except (ValueError, TypeError):
                return 0
        return expiry_time or 0

    # Sort clients using the custom key function
    clients.sort(key=get_sort_key, reverse=True)

    # Pagination settings
    items_per_page = 5
    total_pages = (len(clients) + items_per_page - 1) // items_per_page
    page = max(0, min(page, total_pages - 1))  # Ensure page is within valid range
    start_index = page * items_per_page
    end_index = min(start_index + items_per_page, len(clients))
    current_page_clients = clients[start_index:end_index]

    # Generate the message with client information
    message = f"👨‍💻 لیست کلاینت ها (صفحه {page + 1} از {total_pages}):\n"
    message += f"📊 تعداد کل: {len(clients)} | 🔌 پنل: {len(xui_clients)} | 💾 دیتابیس: {len(db_clients)}\n\n"

    for i, client in enumerate(current_page_clients, start=1):
        email = client.get('email', 'بدون نام')
        total_gb = client.get('total_gb', client.get('totalGB', 0) / (1024 ** 3))
        remaining_gb = client.get('remaining_gb', 0)
        expiry_date = client.get('expiry_date', 'نامشخص')
        active_status = "✅ فعال" if client.get('is_active', client.get('enable', False)) else "❌ غیرفعال"
        remaining_time = client.get('remaining_time_display', 'نامشخص')

        # Location indicators
        location = ""
        if client.get('in_xui', False) and client.get('in_db', False):
            location = "📱💾" # In both XUI and DB
        elif client.get('in_xui', False):
            location = "📱"  # Only in XUI
        elif client.get('in_db', False):
            location = "💾"  # Only in DB

        # User information
        user_info = ""
        if client.get('username') or client.get('first_name'):
            user_info = f"👤 کاربر: {client.get('first_name', '')} (@{client.get('username', '')})\n   "

        message += (
            f"{i}. {location} {email}\n"
            f"   {user_info}📊 حجم: {remaining_gb}/{total_gb} GB\n"
            f"   ⏳ زمان: {remaining_time} (تا {expiry_date})\n"
            f"   🔌 وضعیت: {active_status}\n"
            f"   🆔 شناسه: {client.get('id', 'نامشخص')[:8]}...\n\n"
        )

    # Create pagination and action buttons
    keyboard = []

    # Add buttons for each client on the current page
    for i, client in enumerate(current_page_clients, start=1):
        client_id = client.get('id', '')
        email = client.get('email', 'بدون نام')
        if client_id:
            keyboard.append([
                InlineKeyboardButton(f"❌ حذف {email}", callback_data=f"admin_delete_client_{client_id}")
            ])

    # Add pagination navigation
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin_clients_page_{page - 1}"))
    if page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton("➡️ بعدی", callback_data=f"admin_clients_page_{page + 1}"))
    if navigation_buttons:
        keyboard.append(navigation_buttons)

    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")])

    # Save current client list in context for later use
    context.user_data['client_list'] = clients

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_delete_client(query, client_id, admin_ids=config.ADMIN_IDS):
    """Ask for confirmation before deleting a client"""
    if admin_ids is None:
        admin_ids = []

    if query.from_user.id not in admin_ids:
        await query.answer("دسترسی رد شد.")
        return

    await query.edit_message_text(
        f"⚠️ آیا از حذف کلاینت با شناسه {client_id[:8]}... اطمینان دارید؟\n"
        "این عملیات غیرقابل بازگشت است!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"admin_confirm_delete_{client_id}")],
            [InlineKeyboardButton("❌ خیر، انصراف", callback_data=f"admin_cancel_delete_{client_id}")]
        ])
    )

async def delete_client_handler(query, client_id, admin_ids=config.ADMIN_IDS):
    """Handle client deletion after confirmation"""
    if admin_ids is None:
        admin_ids = []

    if query.from_user.id not in admin_ids:
        await query.answer("��سترسی رد شد.")
        return

    # Import delete_client function
    from xui_api import delete_client
    from db_utils import delete_config_by_client_id

    # Delete the client from XUI panel
    success, error_message = delete_client(client_id)

    if success:
        # If deletion from XUI panel was successful, also delete from database
        db_success = delete_config_by_client_id(client_id)

        message = f"✅ کلاینت با شناسه {client_id[:8]}... با موفقیت حذف شد."
        if db_success:
            message += "\n✅ اطلاعات مربوطه از دیتابیس نیز حذف شد."
        else:
            message += "\n⚠️ حذف از دیتابیس ناموفق بود. کاربران ممکن است همچنان کانفیگ را در لیست خود مشاهده کنند."

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به لیست کلاینت ها", callback_data="admin_manage_clients")],
                [InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin_menu")]
            ])
        )
    else:
        await query.edit_message_text(
            f"❌ خطا در حذف کلاینت:\n{error_message}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تلاش مجدد", callback_data=f"admin_delete_client_{client_id}")],
                [InlineKeyboardButton("🔙 بازگشت به لیست کلاینت ها", callback_data="admin_manage_clients")],
                [InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin_menu")]
            ])
        )

async def cancel_delete_client(query, client_id, context, admin_ids=config.ADMIN_IDS):
    """Cancel client deletion and return to client list"""
    if admin_ids is None:
        admin_ids = []

    if query.from_user.id not in admin_ids:
        await query.answer("دسترسی رد شد.")
        return

    # Return to the client list
    await show_all_clients(query, context, admin_ids=admin_ids)
