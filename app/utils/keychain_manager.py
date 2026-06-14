import logging
import json
import os
import time
import ctypes
import sys

logger = logging.getLogger("karl.keychain")

try:
    import keyring
except ImportError:
    keyring = None

# ── Linux Kernel Keyring (keyutils) ──────────────────────────────────────────
_libkeyutils = None
_KEY_SPEC_SESSION_KEYRING = -3

if sys.platform == "linux":
    try:
        # Standard location on most distros (Debian/Ubuntu/Arch).
        # use_errno=True lets ctypes.get_errno() read the C errno after each call.
        _libkeyutils = ctypes.CDLL('libkeyutils.so.1', use_errno=True)
    except Exception:
        try:
            _libkeyutils = ctypes.CDLL('libkeyutils.so', use_errno=True)
        except Exception:
            _libkeyutils = None

# ── x86_64 syscall numbers & keyctl subcommand constants ─────────────────────
_SYS_ADD_KEY        = 248          # add_key(2)  — x86_64 Linux ABI
_SYS_KEYCTL         = 250          # keyctl(2)   — x86_64 Linux ABI
_KEYCTL_REVOKE      = ctypes.c_long(3)   # keyctl subcommand: destroy a key
_KEYCTL_SET_TIMEOUT = ctypes.c_long(15)  # keyctl subcommand: set expiry

# ─────────────────────────────────────────────────────────────────────────────

SERVICE_NAME = "KarlBridge"
USER_NAME = "BridgeToken"
TOKEN_PATH = "data/bridge_token.json"
TOKEN_LIFETIME = 43200  # 12 hours


def save_cached_token(token: str):
    """Stores the bridge token securely in the Kernel Keyring (Linux) or OS keychain."""
    
    # 1. Try Linux Kernel Keyring first
    if _libkeyutils:
        try:
            # add_key(type, description, payload, plen, keyring)
            res = _libkeyutils.add_key(
                b"user", 
                b"karl_token", 
                token.encode(), 
                len(token), 
                _KEY_SPEC_SESSION_KEYRING
            )
            if res != -1:
                logger.info("Bridge token cached in Linux Kernel Keyring.")
                # We still save to user-space keyring as a persistent fallback
                # if the session keyring is volatile (depends on PAM config)
        except Exception as e:
            logger.debug(f"Kernel keyring save failed: {e}")

    # 2. Standard OS Keychain fallback
    if not keyring:
        return

    try:
        keyring.set_password(SERVICE_NAME, USER_NAME, token)
        logger.info("Bridge token cached in OS keychain.")
    except Exception as e:
        logger.warning(f"Failed to cache token in OS keychain: {e}")


def load_cached_token() -> str | None:
    """
    Retrieves the bridge token and verifies it against the 12-hour window.
    Checks Kernel Keyring (Linux) first, then falls back to OS Keychain.
    """
    
    # 1. Try Linux Kernel Keyring
    if _libkeyutils:
        try:
            # request_key(type, description, callout_info, keyring)
            key_id = _libkeyutils.request_key(
                b"user", 
                b"karl_token", 
                None, 
                _KEY_SPEC_SESSION_KEYRING
            )
            if key_id != -1:
                # keyctl_read(key, buffer, buflen)
                # First call with None buffer returns actual length
                needed = _libkeyutils.keyctl_read(key_id, None, 0)
                if needed > 0:
                    buf = ctypes.create_string_buffer(needed)
                    read = _libkeyutils.keyctl_read(key_id, buf, needed)
                    if read != -1:
                        token = buf.value.decode('utf-8')
                        # Active-zero the mutable buffer to purge key material from process memory
                        ctypes.memset(buf, 0, needed)
                        
                        if _verify_token(token):
                            logger.info("Auth: Using token from Linux Kernel Keyring.")
                            return token
        except Exception as e:
            logger.debug(f"Kernel keyring retrieval failed: {e}")

    # 2. Try OS Keychain
    if not keyring:
        return None

    try:
        token = keyring.get_password(SERVICE_NAME, USER_NAME)
        if token and _verify_token(token):
            return token
    except Exception as e:
        logger.warning(f"OS keychain access failed or locked: {e}")
    
    return None


def revoke_tokens():
    """Purges the bridge token from the kernel keyring and OS keychain."""
    # 1. Kernel Keyring
    if _libkeyutils:
        try:
            key_id = _libkeyutils.request_key(
                b"user", 
                b"karl_token", 
                None, 
                _KEY_SPEC_SESSION_KEYRING
            )
            if key_id != -1:
                # keyctl_revoke or keyctl_unlink
                _libkeyutils.keyctl_revoke(key_id)
                logger.debug("Bridge token revoked from Kernel Keyring.")
        except Exception:
            pass

    # 2. OS Keychain
    _clear_keyring()


def _verify_token(token: str) -> bool:
    """Helper to check token against disk state and time limit."""
    if not os.path.exists(TOKEN_PATH):
        return False
        
    try:
        with open(TOKEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if token != data.get("token"):
            return False

        if time.time() - data.get("created_at", 0) > TOKEN_LIFETIME:
            logger.info("Cached token expired.")
            return False

        return True
    except Exception:
        return False


def _clear_keyring():
    """Removes the bridge token from the OS keychain."""
    if not keyring:
        return
    try:
        keyring.delete_password(SERVICE_NAME, USER_NAME)
    except Exception:
        pass


# ── Low-level kernel-keyring helpers ─────────────────────────────────────────
# Each helper explicitly sets argtypes and restype before every call so that
# ctypes never has to guess the C types on a 64-bit platform.

def _add_key_kernel(
    key_type: bytes,
    description: bytes,
    payload: bytes,
    keyring: int,
) -> int:
    """
    Call add_key() via libkeyutils (preferred) or the raw x86_64 syscall (248).

    All argtypes and restype are declared before invocation to prevent pointer
    misalignment on 64-bit platforms. Returns the key_serial_t (≥ 0) on
    success, or a negative value on failure.
    """
    plen = ctypes.c_size_t(len(payload))
    ring = ctypes.c_int32(keyring)   # key_serial_t is int32_t

    if _libkeyutils is not None:
        fn = _libkeyutils.add_key
        fn.argtypes = [
            ctypes.c_char_p,   # const char *type
            ctypes.c_char_p,   # const char *description
            ctypes.c_char_p,   # const void *payload  (bytes are fine here)
            ctypes.c_size_t,   # size_t plen
            ctypes.c_int32,    # key_serial_t ringid
        ]
        fn.restype = ctypes.c_int32
        return int(fn(key_type, description, payload, plen, ring))

    # Syscall fallback — x86_64 Linux only
    if sys.platform != "linux":
        return -1
    libc = ctypes.CDLL(None, use_errno=True)
    sc = libc.syscall
    sc.argtypes = [
        ctypes.c_long,     # syscall number
        ctypes.c_char_p,   # type
        ctypes.c_char_p,   # description
        ctypes.c_char_p,   # payload
        ctypes.c_size_t,   # plen
        ctypes.c_int32,    # keyring (key_serial_t)
    ]
    sc.restype = ctypes.c_long
    return int(sc(_SYS_ADD_KEY, key_type, description, payload, plen, ring))


def _keyctl_timeout(key_id: int, timeout_seconds: int) -> None:
    """
    Set *timeout_seconds* expiry on *key_id* via keyctl_set_timeout (libkeyutils)
    or the keyctl syscall (250, subcommand KEYCTL_SET_TIMEOUT = 15).
    Logs a warning on failure but does not raise — a missing timeout is
    recoverable; the key still exists in the keyring.
    """
    kid = ctypes.c_int32(key_id)
    tmo = ctypes.c_uint(timeout_seconds)

    if _libkeyutils is not None:
        fn = _libkeyutils.keyctl_set_timeout
        fn.argtypes = [ctypes.c_int32, ctypes.c_uint]
        fn.restype  = ctypes.c_long
        if int(fn(kid, tmo)) == -1:
            ev = ctypes.get_errno()
            logger.warning(
                "keyctl_set_timeout(%d, %d) failed: errno=%d (%s)",
                key_id, timeout_seconds, ev, os.strerror(ev) if ev else "?",
            )
        return

    if sys.platform != "linux":
        return
    libc = ctypes.CDLL(None, use_errno=True)
    sc = libc.syscall
    sc.argtypes = [
        ctypes.c_long,   # syscall number
        ctypes.c_long,   # KEYCTL_SET_TIMEOUT
        ctypes.c_int32,  # key_id
        ctypes.c_uint,   # timeout
    ]
    sc.restype = ctypes.c_long
    if int(sc(_SYS_KEYCTL, _KEYCTL_SET_TIMEOUT, kid, tmo)) == -1:
        ev = ctypes.get_errno()
        logger.warning(
            "keyctl syscall SET_TIMEOUT(%d, %d) failed: errno=%d (%s)",
            key_id, timeout_seconds, ev, os.strerror(ev) if ev else "?",
        )


def _keyctl_revoke_key(key_id: int) -> None:
    """
    Destroy *key_id* via keyctl_revoke (libkeyutils) or the keyctl syscall
    (250, subcommand KEYCTL_REVOKE = 3). Raises RuntimeError on failure.
    """
    kid = ctypes.c_int32(key_id)

    if _libkeyutils is not None:
        fn = _libkeyutils.keyctl_revoke
        fn.argtypes = [ctypes.c_int32]
        fn.restype  = ctypes.c_long
        if int(fn(kid)) == -1:
            ev = ctypes.get_errno()
            raise RuntimeError(
                f"keyctl_revoke({key_id}) failed: "
                f"errno={ev} ({os.strerror(ev) if ev else '?'})"
            )
        return

    if sys.platform != "linux":
        raise RuntimeError(
            "revoke_session_token: Linux Kernel Keyring is not available on this platform."
        )
    libc = ctypes.CDLL(None, use_errno=True)
    sc = libc.syscall
    sc.argtypes = [
        ctypes.c_long,   # syscall number
        ctypes.c_long,   # KEYCTL_REVOKE
        ctypes.c_int32,  # key_id
    ]
    sc.restype = ctypes.c_long
    if int(sc(_SYS_KEYCTL, _KEYCTL_REVOKE, kid)) == -1:
        ev = ctypes.get_errno()
        raise RuntimeError(
            f"keyctl syscall REVOKE({key_id}) failed: "
            f"errno={ev} ({os.strerror(ev) if ev else '?'})"
        )


# ── Public API ────────────────────────────────────────────────────────────────

def store_session_token(token: str, timeout_seconds: int = 43200) -> int:
    """
    Store *token* in the Linux Kernel Session Keyring and arm an auto-expiry.

    Key type    : ``user``
    Description : ``KarlBridgeToken``
    Keyring     : ``KEY_SPEC_SESSION_KEYRING`` (-3)

    Uses libkeyutils when available; falls back to the raw x86_64 syscall
    (add_key = 248, keyctl = 250) so the call succeeds even on minimal Arch
    installs without the keyutils user-space library.

    All ctypes argtypes and restype are explicitly declared before invocation
    to prevent memory corruption or pointer misalignment on 64-bit platforms.

    Args:
        token:           Plaintext session token string.
        timeout_seconds: Key lifetime in seconds (default 43 200 = 12 hours).

    Returns:
        The integer key ID (``key_serial_t``) assigned by the kernel.

    Raises:
        RuntimeError: When both the library call and the syscall fallback fail,
                      or when called outside Linux.
    """
    if sys.platform != "linux":
        raise RuntimeError(
            "store_session_token: Linux Kernel Keyring is only available on Linux."
        )

    payload = token.encode("utf-8")
    key_id = _add_key_kernel(
        key_type=b"user",
        description=b"KarlBridgeToken",
        payload=payload,
        keyring=_KEY_SPEC_SESSION_KEYRING,
    )

    if key_id < 0:
        ev = ctypes.get_errno()
        raise RuntimeError(
            f"add_key() failed: returned {key_id}, "
            f"errno={ev} ({os.strerror(ev) if ev else 'unknown error'})"
        )

    _keyctl_timeout(key_id, timeout_seconds)

    logger.info(
        "Session token stored in kernel keyring: key_id=%d timeout=%ds",
        key_id, timeout_seconds,
    )
    return key_id


def revoke_session_token(key_id: int) -> None:
    """
    Explicitly destroy the kernel keyring entry identified by *key_id*.

    Invokes ``keyctl_revoke`` (libkeyutils) or the ``keyctl`` syscall
    (subcommand ``KEYCTL_REVOKE`` = 3) with fully declared argtypes/restype.

    Args:
        key_id: The integer key ID returned by ``store_session_token()``.

    Raises:
        RuntimeError: When the revocation call fails at the kernel level, or
                      when called outside Linux.
    """
    if sys.platform != "linux":
        raise RuntimeError(
            "revoke_session_token: Linux Kernel Keyring is only available on Linux."
        )

    _keyctl_revoke_key(key_id)
    logger.info("Session key %d revoked from kernel keyring.", key_id)
