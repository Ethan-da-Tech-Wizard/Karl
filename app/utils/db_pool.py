"""
Thread-safe SQLite connection pool for Karl's metadata store.
"""

import queue
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator


class SQLiteConnectionPool:
    """
    Pre-configured pool of SQLite connections pointing to a single database file.

    Each connection is set up with WAL journal mode, NORMAL synchronous writes,
    and a 30-second busy timeout so concurrent threads queue up at the SQLite
    level instead of raising SQLITE_BUSY immediately.
    """

    def __init__(self, db_path: str, pool_size: int = 5) -> None:
        self._db_path = db_path
        self._pool_size = pool_size
        self._semaphore = threading.Semaphore(pool_size)
        self._queue: queue.Queue[sqlite3.Connection] = queue.Queue(maxsize=pool_size)
        for _ in range(pool_size):
            self._queue.put(self._make_connection())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _make_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self._db_path,
            timeout=30.0,
            isolation_level=None,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    # ── Public API ────────────────────────────────────────────────────────────

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Yield a connection from the pool and return it on exit.

        The semaphore limits concurrent holders to pool_size; get_nowait() is
        safe here because the semaphore guarantees a slot is available.
        """
        self._semaphore.acquire()
        conn = self._queue.get_nowait()
        try:
            yield conn
        finally:
            self._queue.put(conn)
            self._semaphore.release()

    def close_all(self) -> None:
        """Close every connection currently in the pool."""
        while True:
            try:
                conn = self._queue.get_nowait()
                conn.close()
            except queue.Empty:
                break
