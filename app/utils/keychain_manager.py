import logging
import json
import os
import time

logger = logging.getLogger("karl.keychain")

try:
    import keyring
except ImportError:
    keyring = None


SERVICE_NAME = "KarlBridge"
USER_NAME = "BridgeToken"
TOKEN_PATH = "data/bridge_token.json"
TOKEN_LIFETIME = 43200  # 12 hours


def save_cached_token(token: str):
    """Stores the bridge token securely in the OS keychain."""
    if not keyring:
        return

    try:
        keyring.set_password(SERVICE_NAME, USER_NAME, token)
        logger.info("Bridge token cached in OS keychain.")
    except Exception as e:
        logger.warning(f"Failed to cache token in OS keychain: {e}")


def load_cached_token() -> str | None:
    """
    Retrieves the bridge token from the OS keychain and verifies it 
    against the local JSON file and the 12-hour expiry window.
    """
    if not keyring:
        return None

    try:
        token = keyring.get_password(SERVICE_NAME, USER_NAME)
        if not token:
            return None

        # Verify against bridge_token.json
        if not os.path.exists(TOKEN_PATH):
            _clear_keyring()
            return None

        try:
            with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            stored_token = data.get("token")
            created_at = data.get("created_at", 0)

            if token != stored_token:
                logger.debug("Keychain token mismatch with disk. Clearing.")
                _clear_keyring()
                return None

            if time.time() - created_at > TOKEN_LIFETIME:
                logger.info("Cached token expired. Clearing.")
                _clear_keyring()
                return None

            return token
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Error verifying cached token: {e}")
            return None

    except Exception as e:
        # Handle locked keyring, DBus errors, etc.
        logger.warning(f"OS keychain access failed or locked: {e}")
        return None


def _clear_keyring():
    """Removes the bridge token from the OS keychain."""
    if not keyring:
        return
    try:
        keyring.delete_password(SERVICE_NAME, USER_NAME)
    except Exception:
        pass
