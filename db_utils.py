"""
Additional database utilities for VPN Bot
"""
import sqlite3
import logging
from config import DB_FILE

logger = logging.getLogger(__name__)

def delete_config_by_client_id(client_id):
    """Delete a configuration from the database by client_id

    Args:
        client_id (str): The client ID to delete

    Returns:
        bool: True if successful, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Find the config_id first (needed for cascading deletions)
        cursor.execute('SELECT config_id FROM configs WHERE client_id = ?', (client_id,))
        result = cursor.fetchone()

        if not result:
            logger.warning(f"No config found with client_id: {client_id}")
            return False

        config_id = result[0]

        # Delete related records in status_logs first due to foreign key constraint
        cursor.execute('DELETE FROM status_logs WHERE config_id = ?', (config_id,))

        # Delete the config record
        cursor.execute('DELETE FROM configs WHERE client_id = ?', (client_id,))

        deleted_count = cursor.rowcount
        conn.commit()

        logger.info(f"Deleted config with client_id: {client_id} (affected rows: {deleted_count})")
        return deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting config with client_id {client_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_db_configs():
    """Get all client configurations from the database

    Returns:
        list: List of client configurations with user information
    """
    import sqlite3
    from config import DB_FILE

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()

    try:
        # Join configs with users table to get user information
        cursor.execute('''
        SELECT 
            c.config_id, c.user_id, c.email, c.client_id, c.total_gb, 
            c.created_at, c.is_active, c.last_notified,
            u.username, u.first_name
        FROM configs c
        LEFT JOIN users u ON c.user_id = u.user_id
        ORDER BY c.created_at DESC
        ''')

        # Convert to list of dictionaries for easier access
        configs = [dict(row) for row in cursor.fetchall()]
        return configs
    except Exception as e:
        logger.error(f"Error retrieving configs from database: {e}")
        return []
    finally:
        conn.close()
