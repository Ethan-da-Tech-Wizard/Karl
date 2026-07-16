import logging
import json
import os
import time
import ctypes
import sys

logger = logging.getLogger("karl.keychain")

try:
    if os.environ.get("KARL_NO_KEYRING") == "1":
        keyring = None
    elif sys.platform == "linux" and not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        logger.info("D-Bus session address not found. Disabling OS keychain fallback.")
        keyring = None
    else:
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
_SYS_ADD_KEY        = 248          # add_key(2)      — x86_64 Linux ABI
_SYS_REQUEST_KEY    = 249          # request_key(2)  — x86_64 Linux ABI
_SYS_KEYCTL         = 250          # keyctl(2)       — x86_64 Linux ABI
_KEYCTL_REVOKE      = ctypes.c_long(3)   # keyctl subcommand: destroy a key
_KEYCTL_READ        = ctypes.c_long(11)  # keyctl subcommand: read key payload
_KEYCTL_SET_TIMEOUT = ctypes.c_long(15)  # keyctl subcommand: set expiry

# ─────────────────────────────────────────────────────────────────────────────

SERVICE_NAME = "KarlBridge"
USER_NAME = "BridgeToken"
TOKEN_PATH = "data/bridge_token.json"
TOKEN_LIFETIME = 43200  # 12 hours

# Canonical scope set — ordered from least to most privileged.
FULL_SCOPES: list[str] = [
    "read:telemetry",
    "read:kb",
    "write:kb",
    "admin:execute",
]

# Predefined role bundles for --generate-key --scope <role>
ROLE_SCOPES: dict[str, list[str]] = {
    "read:telemetry": ["read:telemetry"],
    "read:kb":        ["read:telemetry", "read:kb"],
    "write:kb":       ["read:telemetry", "read:kb", "write:kb"],
    "admin:execute":  list(FULL_SCOPES),
}


def save_cached_token(token: str):
    """Stores the bridge token securely in the Kernel Keyring (Linux) or OS keychain."""

    # 1. Try Linux Kernel Keyring first — via the hardened helper below, which
    # declares argtypes/restype explicitly (see its docstring) rather than
    # letting ctypes guess the C ABI.
    if sys.platform == "linux":
        try:
            key_id = _add_key_kernel(
                key_type=b"user",
                description=b"karl_token",
                payload=token.encode(),
                keyring=_KEY_SPEC_SESSION_KEYRING,
            )
            if key_id >= 0:
                logger.info("Bridge token cached in Linux Kernel Keyring.")
                # We still save to user-space keyring as a persistent fallback
                # if the session keyring is volatile (depends on PAM config)
        except Exception as e:
            logger.debug(f"Kernel keyring save failed: {e}")

    # 2. Standard OS Keychain fallback
    if not keyring:
        return

    try:
        _set_password_with_timeout(SERVICE_NAME, USER_NAME, token)
        logger.info("Bridge token cached in OS keychain.")
    except Exception as e:
        logger.warning(f"Failed to cache token in OS keychain: {e}")


def load_cached_token() -> str | None:
    """
    Retrieves the bridge token and verifies it against the 12-hour window.
    Checks Kernel Keyring (Linux) first, then falls back to OS Keychain.
    """
    
    # 1. Try Linux Kernel Keyring — via the hardened helpers, which declare
    # argtypes/restype explicitly rather than letting ctypes guess the ABI.
    if sys.platform == "linux":
        try:
            key_id = _request_key_kernel(b"user", b"karl_token", _KEY_SPEC_SESSION_KEYRING)
            if key_id >= 0:
                payload = _keyctl_read_kernel(key_id)
                if payload:
                    token = payload.decode('utf-8')
                    if _verify_token(token):
                        logger.info("Auth: Using token from Linux Kernel Keyring.")
                        return token
        except Exception as e:
            logger.debug(f"Kernel keyring retrieval failed: {e}")

    # 2. Try OS Keychain
    if not keyring:
        return None

    try:
        token = _get_password_with_timeout(SERVICE_NAME, USER_NAME)
        if token and _verify_token(token):
            return token
    except Exception as e:
        logger.warning(f"OS keychain access failed or locked: {e}")

    return None


def _call_keyring_with_timeout(fn, *args, timeout: float = 3.0):
    """
    Calls a blocking `keyring` function with a hard wall-clock timeout.

    Some OS keychain backends — notably the Linux SecretService/D-Bus
    backend when no prompt-handling agent is available to answer an unlock
    request — can block indefinitely. Both save_cached_token() and
    load_cached_token() can be reached from the GUI thread during startup
    (see FlywheelStudioWorkspace._auto_authorize_logs and
    WebSocketServerManager._init_security, both of which moved their own
    call site off the GUI thread specifically because of this), where an
    unbounded block would freeze the entire application before the window
    ever paints, with no visible error. Python has no API to forcibly kill
    a blocked thread, so on timeout this abandons the call (the underlying
    thread keeps running harmlessly in the background, un-joined, until/if
    it ever returns) and raises TimeoutError instead of letting the caller
    hang.
    """
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        logger.warning(
            "OS keychain call (%s) exceeded %.1fs (backend may be waiting "
            "on an unlock prompt); giving up for this call.",
            getattr(fn, "__name__", fn), timeout,
        )
        raise TimeoutError(f"keyring.{getattr(fn, '__name__', fn)} timed out after {timeout}s")
    finally:
        executor.shutdown(wait=False)


def _get_password_with_timeout(service: str, user: str, timeout: float = 3.0) -> str | None:
    """Calls keyring.get_password() with a hard wall-clock timeout (see
    _call_keyring_with_timeout). Returns None on timeout — a missing
    password is an ordinary, expected outcome for a get."""
    try:
        return _call_keyring_with_timeout(keyring.get_password, service, user, timeout=timeout)
    except TimeoutError:
        return None


def _set_password_with_timeout(service: str, user: str, password: str, timeout: float = 3.0) -> None:
    """Calls keyring.set_password() with a hard wall-clock timeout (see
    _call_keyring_with_timeout). Re-raises on timeout so the caller's
    existing `except Exception` handling logs the failure to persist."""
    _call_keyring_with_timeout(keyring.set_password, service, user, password, timeout=timeout)


def revoke_tokens():
    """Purges the bridge token from the kernel keyring and OS keychain."""
    # 1. Kernel Keyring — via the hardened helpers (see save_cached_token).
    if sys.platform == "linux":
        try:
            key_id = _request_key_kernel(b"user", b"karl_token", _KEY_SPEC_SESSION_KEYRING)
            if key_id >= 0:
                _keyctl_revoke_key(key_id)
                logger.debug("Bridge token revoked from Kernel Keyring.")
        except Exception:
            pass

    # 2. OS Keychain
    _clear_keyring()


def get_token_scopes(token: str, token_path: str = TOKEN_PATH) -> list[str] | None:
    """Return the scope list for *token* from the on-disk store, or None if invalid/expired."""
    if not token or not os.path.exists(token_path):
        return None
    try:
        with open(token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "tokens" in data:
            scopes = data["tokens"].get(token)
            created_at = float(data.get("created_at", 0))
        else:
            # Legacy single-token format
            scopes = FULL_SCOPES if token == data.get("token") else None
            created_at = float(data.get("created_at", 0))
        if scopes is None:
            return None
        if time.time() - created_at > TOKEN_LIFETIME:
            logger.info("Cached token expired.")
            return None
        return list(scopes)
    except Exception:
        return None


def add_scoped_token(token: str, scopes: list[str], token_path: str = TOKEN_PATH) -> None:
    """Register *token* with *scopes* in the on-disk token store.

    Creates the file if it does not exist. Preserves existing tokens.
    """
    dir_ = os.path.dirname(token_path)
    if dir_:
        os.makedirs(dir_, exist_ok=True)
    data: dict = {}
    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    # Migrate old single-token format on the fly
    if "tokens" not in data:
        old_tok = data.get("token")
        data = {
            "tokens": {old_tok: list(FULL_SCOPES)} if old_tok else {},
            "created_at": data.get("created_at", time.time()),
        }
    data["tokens"][token] = list(scopes)
    # Bearer tokens (including admin:execute-scoped ones) are stored here in
    # plaintext, so restrict the file to the owner before any content is
    # written — os.open with an explicit mode avoids a window where a
    # default-umask file briefly exists before a later chmod() would apply.
    fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.chmod(token_path, 0o600)
    logger.info("Scoped token registered: scopes=%s path=%s", scopes, token_path)


def _verify_token(token: str) -> bool:
    """Helper to check token against disk state and time limit."""
    return get_token_scopes(token) is not None


def _clear_keyring():
    """Removes the bridge token from the OS keychain.

    revoke_tokens() (and therefore this) runs synchronously from
    MainWindow.closeEvent() on the GUI thread during app shutdown — bound
    with the same timeout as save_cached_token/load_cached_token so a
    hung SecretService/D-Bus backend can't also freeze the app on exit.
    """
    if not keyring:
        return
    try:
        _call_keyring_with_timeout(keyring.delete_password, SERVICE_NAME, USER_NAME)
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


def _request_key_kernel(key_type: bytes, description: bytes, keyring: int) -> int:
    """
    Call request_key() via libkeyutils (preferred) or the raw x86_64 syscall
    (249). All argtypes and restype are declared before invocation, same as
    _add_key_kernel above. Returns the key_serial_t (>= 0) on success, or a
    negative value if the key wasn't found / the call failed.
    """
    ring = ctypes.c_int32(keyring)

    if _libkeyutils is not None:
        fn = _libkeyutils.request_key
        fn.argtypes = [
            ctypes.c_char_p,   # const char *type
            ctypes.c_char_p,   # const char *description
            ctypes.c_char_p,   # const char *callout_info (NULL here)
            ctypes.c_int32,    # key_serial_t dest_keyring
        ]
        fn.restype = ctypes.c_int32
        return int(fn(key_type, description, None, ring))

    if sys.platform != "linux":
        return -1
    libc = ctypes.CDLL(None, use_errno=True)
    sc = libc.syscall
    sc.argtypes = [
        ctypes.c_long,     # syscall number
        ctypes.c_char_p,   # type
        ctypes.c_char_p,   # description
        ctypes.c_char_p,   # callout_info
        ctypes.c_int32,    # dest_keyring
    ]
    sc.restype = ctypes.c_long
    return int(sc(_SYS_REQUEST_KEY, key_type, description, None, ring))


def _keyctl_read_kernel(key_id: int) -> bytes | None:
    """
    Read the payload of *key_id* via keyctl_read (libkeyutils) or the keyctl
    syscall (250, subcommand KEYCTL_READ = 11), with argtypes/restype
    declared before every call. Returns the raw payload bytes, or None if
    the key is empty/unreadable. The backing ctypes buffer is zeroed before
    this function returns (best-effort — see _zero_bytes usage elsewhere for
    why the returned Python bytes object itself can't be scrubbed).
    """
    kid = ctypes.c_int32(key_id)

    if _libkeyutils is not None:
        fn = _libkeyutils.keyctl_read
        fn.argtypes = [ctypes.c_int32, ctypes.c_char_p, ctypes.c_size_t]
        fn.restype = ctypes.c_long
        needed = int(fn(kid, None, 0))
        if needed <= 0:
            return None
        buf = ctypes.create_string_buffer(needed)
        read = int(fn(kid, buf, ctypes.c_size_t(needed)))
        if read < 0:
            return None
        data = buf.raw[:read]
        ctypes.memset(buf, 0, needed)
        return data

    if sys.platform != "linux":
        return None
    libc = ctypes.CDLL(None, use_errno=True)
    sc = libc.syscall
    sc.argtypes = [
        ctypes.c_long,    # syscall number
        ctypes.c_long,    # KEYCTL_READ
        ctypes.c_int32,   # key_id
        ctypes.c_char_p,  # buffer
        ctypes.c_size_t,  # buflen
    ]
    sc.restype = ctypes.c_long
    needed = int(sc(_SYS_KEYCTL, _KEYCTL_READ, kid, None, 0))
    if needed <= 0:
        return None
    buf = ctypes.create_string_buffer(needed)
    read = int(sc(_SYS_KEYCTL, _KEYCTL_READ, kid, buf, ctypes.c_size_t(needed)))
    if read < 0:
        return None
    data = buf.raw[:read]
    ctypes.memset(buf, 0, needed)
    return data


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
