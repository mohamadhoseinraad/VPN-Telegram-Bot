"""
XUI Panel API interactions
"""
import requests
import json
import logging
import time
from datetime import datetime, timedelta
import uuid
from config import XUI_URL, XUI_USERNAME, XUI_PASSWORD, INBOUND_ID

logger = logging.getLogger(__name__)
session = requests.Session()
_session_authenticated = False
_last_login_time = 0
# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800

def login_to_xui(force=False):
    """Login to the XUI panel

    Args:
        force (bool): Force re-login even if session is still valid

    Returns:
        bool: True if login successful, False otherwise
    """
    global _session_authenticated, _last_login_time

    # If already logged in and session is fresh, don't re-login unless forced
    current_time = time.time()
    if _session_authenticated and (current_time - _last_login_time) < SESSION_TIMEOUT and not force:
        return True

    url = f"{XUI_URL}/login"
    data = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        response = session.post(url, json=data)
        if response.ok:
            _session_authenticated = True
            _last_login_time = current_time
            logger.info("Successfully logged in to XUI panel")
            return True
        else:
            _session_authenticated = False
            logger.error(f"Login failed with status code: {response.status_code}")
            return False
    except Exception as e:
        _session_authenticated = False
        logger.error(f"Exception during login: {e}")
        return False

def ensure_authenticated():
    """Ensure the session is authenticated, attempt re-login if needed

    Returns:
        bool: True if authenticated, False otherwise
    """
    global _session_authenticated

    # Try using current session
    if _session_authenticated:
        return True

    # Session not authenticated, attempt login
    return login_to_xui()

def get_client_status(email):
    """Get the status of a client by email"""
    if not ensure_authenticated():
        return None

    response = session.get(f"{XUI_URL}/panel/api/inbounds/getClientTraffics/{email}")
    # If unauthorized, try logging in again and retry
    if response.status_code == 401:
        if login_to_xui(force=True):
            response = session.get(f"{XUI_URL}/panel/api/inbounds/getClientTraffics/{email}")
        else:
            return None

    if not response.ok:
        return None

    try:
        data = response.json().get('obj', {})
        if not data:
            return None

        total_bytes = data.get('total', 0)
        used_bytes = data.get('up', 0) + data.get('down', 0)
        remaining_bytes = max(0, total_bytes - used_bytes)
        remaining_gb = round(remaining_bytes / (1024 ** 3), 2)

        expiry_time = data.get('expiryTime', 0) / 1000
        remaining_seconds = max(0, expiry_time - time.time())

        # Calculate days and hours separately for more precise display
        remaining_days = int(remaining_seconds // 86400)
        remaining_hours = int((remaining_seconds % 86400) // 3600)

        # Format the remaining time display
        if remaining_days > 0:
            remaining_time_display = f"{remaining_days} روز"
            if remaining_hours > 0:
                remaining_time_display += f" و {remaining_hours} ساعت"
        else:
            remaining_time_display = f"{remaining_hours} ساعت"

        return {
            'email': email,
            'remaining_gb': remaining_gb,
            'remaining_days': remaining_days,
            'remaining_hours': remaining_hours,
            'remaining_time_display': remaining_time_display,
            'total_gb': round(total_bytes / (1024 ** 3), 2),
            'expiry_date': datetime.fromtimestamp(expiry_time).strftime('%Y-%m-%d'),
            'is_active': data.get('enable', False)
        }
    except Exception as e:
        logger.error(f"Error parsing client status: {e}")
        return None

def create_client(email, total_gb, expiry_time_ms):
    """Create a new client in the XUI panel"""
    if not ensure_authenticated():
        return None, "Failed to login to XUI panel"

    client_id = str(uuid.uuid4())

    settings = {
        "clients": [
            {
                "id": client_id,
                "flow": "",
                "email": email,
                "limitIp": 0,
                "totalGB": total_gb,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "tgId": "",
                "subId": str(uuid.uuid4())[:16],
                "reset": 0
            }
        ]
    }

    payload = {
        "id": INBOUND_ID,
        "settings": json.dumps(settings, ensure_ascii=False)
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = session.post(
            f"{XUI_URL}/panel/api/inbounds/addClient",
            headers=headers,
            json=payload,
            timeout=20
        )
        # If unauthorized, try logging in again and retry
        if response.status_code == 401:
            if login_to_xui(force=True):
                response = session.post(
                    f"{XUI_URL}/panel/api/inbounds/addClient",
                    headers=headers,
                    json=payload,
                    timeout=20
                )

        response.raise_for_status()

        data = response.json()
        if not data.get("success"):
            return None, data.get("msg", "Error adding client")

        return client_id, None
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        return None, str(e)

def extend_client(email, client_id, additional_gb, new_expiry_time_ms=None):
    """Extend an existing client's quota and/or expiry time

    Args:
        email (str): Client's email identifier
        client_id (str): Client's UUID
        additional_gb (int): Additional GB to add to the client's quota
        new_expiry_time_ms (int, optional): New expiry time in milliseconds.
                                           If None, adds 30 days to current expiry.

    Returns:
        tuple: (success (bool), error_message (str or None))
    """
    if not ensure_authenticated():
        return False, "Failed to login to XUI panel"

    # First get current client data
    client_status = get_client_status(email)
    if not client_status:
        return False, "Could not find client information"

    # Calculate new total GB
    current_total_gb = client_status['total_gb']
    new_total_gb = current_total_gb + additional_gb
    total_bytes = int(new_total_gb * (1024 ** 3))  # Convert GB to bytes

    # Calculate new expiry time by adding 30 days to current expiry date
    # If new_expiry_time_ms is provided, use that instead
    # Convert the expiry date from string to timestamp and add 30 days
    expiry_date = datetime.strptime(client_status['expiry_date'], '%Y-%m-%d')
    # Add 30 days to the current expiry date
    new_expiry_date = expiry_date + new_expiry_time_ms
    expiry_time_ms = int(new_expiry_date.timestamp() * 1000)


    # Prepare the settings for client update
    settings = {
        "clients": [
            {
                "id": client_id,
                "flow": "",
                "email": email,
                "limitIp": 0,
                "totalGB": total_bytes,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "tgId": "",
                "subId": client_id[:16],  # Use part of the client_id for consistency
                "reset": 0
            }
        ]
    }

    payload = {
        "id": INBOUND_ID,
        "settings": json.dumps(settings, ensure_ascii=False)
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        # Use the updateClient endpoint with the client's UUID
        response = session.post(
            f"{XUI_URL}/panel/api/inbounds/updateClient/{client_id}",
            headers=headers,
            json=payload,
            timeout=20
        )

        # If unauthorized, try logging in again and retry
        if response.status_code == 401:
            if login_to_xui(force=True):
                response = session.post(
                    f"{XUI_URL}/panel/api/inbounds/updateClient/{client_id}",
                    headers=headers,
                    json=payload,
                    timeout=20
                )

        response.raise_for_status()

        data = response.json()
        if not data.get("success"):
            return False, f"Error updating client: {data.get('msg', 'Unknown error')}"

        return True, None

    except Exception as e:
        logger.error(f"Error extending client: {e}")
        return False, str(e)

def get_all_clients():
    """Get all clients from the XUI panel

    Returns:
        list: List of clients or None if error
    """
    if not ensure_authenticated():
        return None

    try:
        response = session.get(f"{XUI_URL}/panel/api/inbounds/list")

        # If unauthorized, try logging in again and retry
        if response.status_code == 401:
            if login_to_xui(force=True):
                response = session.get(f"{XUI_URL}/panel/api/inbounds/list")
            else:
                return None

        if not response.ok:
            logger.error(f"Failed to get inbounds list: {response.status_code}")
            return None

        data = response.json()
        if not data.get("success"):
            logger.error(f"API error: {data.get('msg', 'Unknown error')}")
            return None

        all_clients = []
        inbounds = data.get("obj", [])

        for inbound in inbounds:
            if str(inbound.get("id")) == str(INBOUND_ID):
                settings = json.loads(inbound.get("settings", "{}"))
                clients = settings.get("clients", [])

                # Include the inbound ID with each client for reference
                for client in clients:
                    client["inboundId"] = inbound.get("id")

                    # Get traffic information for this client
                    if client.get("email"):
                        traffic_info = get_client_status(client.get("email"))
                        if traffic_info:
                            client.update({
                                "remaining_gb": traffic_info.get("remaining_gb"),
                                "total_gb": traffic_info.get("total_gb"),
                                "expiry_date": traffic_info.get("expiry_date"),
                                "remaining_time_display": traffic_info.get("remaining_time_display"),
                                "is_active": traffic_info.get("is_active")
                            })

                all_clients.extend(clients)

        return all_clients
    except Exception as e:
        logger.error(f"Error getting all clients: {e}")
        return None

def delete_client(client_id):
    """Delete a client by UUID

    Args:
        client_id (str): Client UUID to delete

    Returns:
        bool: True if successful, False otherwise
    """
    if not ensure_authenticated():
        return False, "Failed to login to XUI panel"

    try:
        response = session.post(f"{XUI_URL}/panel/api/inbounds/{INBOUND_ID}/delClient/{client_id}")

        # If unauthorized, try logging in again and retry
        if response.status_code == 401:
            if login_to_xui(force=True):
                response = session.post(f"{XUI_URL}/panel/api/inbounds/{INBOUND_ID}/delClient/{client_id}")
            else:
                return False, "Authentication failed"

        if not response.ok:
            return False, f"API request failed with status code: {response.status_code}"

        data = response.json()
        if not data.get("success"):
            return False, f"API error: {data.get('msg', 'Unknown error')}"

        return True, None
    except Exception as e:
        logger.error(f"Error deleting client: {e}")
        return False, str(e)
