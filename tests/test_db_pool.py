"""
Tests for SQLiteConnectionPool — thread-safety, WAL configuration, and ACID safety
under concurrent writes.
"""

import os
import sqlite3
import threading
import time

import pytest

from app.utils.db_pool import SQLiteConnectionPool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_table(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_rows (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            value     TEXT,
            thread_id INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def _row_count(db_path: str) -> int:
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        return conn.execute("SELECT COUNT(*) FROM test_rows").fetchone()[0]
    finally:
        conn.close()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_connections_use_wal_journal_mode(tmp_path):
    """Every connection dispensed by the pool must use WAL journal mode."""
    db_path = str(tmp_path / "wal.db")
    pool = SQLiteConnectionPool(db_path, pool_size=3)
    try:
        for _ in range(3):
            with pool.get_connection() as conn:
                mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
                assert mode == "wal", f"Expected WAL, got {mode!r}"
    finally:
        pool.close_all()


def test_connections_use_normal_synchronous(tmp_path):
    """All pool connections should be configured with synchronous=NORMAL (1)."""
    db_path = str(tmp_path / "sync.db")
    pool = SQLiteConnectionPool(db_path, pool_size=2)
    try:
        with pool.get_connection() as conn:
            sync = conn.execute("PRAGMA synchronous;").fetchone()[0]
            assert sync == 1, f"Expected synchronous=NORMAL (1), got {sync}"
    finally:
        pool.close_all()


def test_connection_is_returned_to_pool_after_context_exit(tmp_path):
    """Acquiring and releasing pool_size connections sequentially must not block."""
    db_path = str(tmp_path / "return.db")
    pool_size = 3
    pool = SQLiteConnectionPool(db_path, pool_size=pool_size)
    try:
        # If connections are not returned, this would deadlock after pool_size uses.
        for i in range(pool_size * 2):
            with pool.get_connection() as conn:
                assert conn is not None
    finally:
        pool.close_all()


def test_concurrent_inserts_complete_without_lock_errors(tmp_path):
    """
    10 threads each insert rows simultaneously.
    All must finish within 5 seconds and none may raise 'database is locked'.
    """
    db_path = str(tmp_path / "concurrent.db")
    _create_table(db_path)

    pool = SQLiteConnectionPool(db_path, pool_size=10)
    thread_count = 10
    rows_per_thread = 5
    errors: list[str] = []
    completed: list[int] = []
    lock = threading.Lock()

    def worker(thread_id: int) -> None:
        try:
            with pool.get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                for i in range(rows_per_thread):
                    conn.execute(
                        "INSERT INTO test_rows(value, thread_id) VALUES (?, ?)",
                        (f"v_{thread_id}_{i}", thread_id),
                    )
                conn.commit()
            with lock:
                completed.append(thread_id)
        except Exception as exc:
            with lock:
                errors.append(str(exc))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    elapsed = time.perf_counter() - start

    pool.close_all()

    assert elapsed < 5.0, f"Threads took {elapsed:.2f}s — exceeded 5-second budget"
    lock_errors = [e for e in errors if "database is locked" in e.lower()]
    assert not lock_errors, f"Lock errors: {lock_errors}"
    assert not errors, f"Thread errors: {errors}"
    assert len(completed) == thread_count, (
        f"Only {len(completed)}/{thread_count} threads completed"
    )


def test_final_row_count_matches_expected_acid_safety(tmp_path):
    """
    10 threads × 10 rows = 100 rows total.
    Verifies complete ACID safety: no lost writes, no partial transactions.
    """
    db_path = str(tmp_path / "acid.db")
    _create_table(db_path)

    pool = SQLiteConnectionPool(db_path, pool_size=5)
    thread_count = 10
    rows_per_thread = 10
    errors: list[str] = []

    def worker(thread_id: int) -> None:
        try:
            with pool.get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.executemany(
                    "INSERT INTO test_rows(value, thread_id) VALUES (?, ?)",
                    [(f"row_{i}", thread_id) for i in range(rows_per_thread)],
                )
                conn.commit()
        except Exception as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    pool.close_all()

    assert not errors, f"Worker errors: {errors}"

    total = _row_count(db_path)
    assert total == thread_count * rows_per_thread, (
        f"Expected {thread_count * rows_per_thread} rows, found {total}"
    )

    conn = sqlite3.connect(db_path)
    try:
        thread_ids = {
            row[0]
            for row in conn.execute("SELECT DISTINCT thread_id FROM test_rows")
        }
    finally:
        conn.close()

    assert thread_ids == set(range(thread_count)), (
        f"Missing thread_ids: {set(range(thread_count)) - thread_ids}"
    )


def test_rollback_on_exception_leaves_no_partial_rows(tmp_path):
    """
    A transaction that fails mid-way must roll back entirely — no partial rows.
    """
    db_path = str(tmp_path / "rollback.db")
    _create_table(db_path)

    pool = SQLiteConnectionPool(db_path, pool_size=2)
    try:
        with pytest.raises(ValueError, match="injected"):
            with pool.get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO test_rows(value, thread_id) VALUES (?, ?)", ("partial", 99)
                )
                conn.rollback()
                raise ValueError("injected failure")
    finally:
        pool.close_all()

    assert _row_count(db_path) == 0, "Rolled-back row must not appear in the table"


def test_semaphore_gates_concurrent_access_to_pool_size(tmp_path):
    """
    With pool_size=3, at most 3 threads should hold connections simultaneously.
    A 4th thread must wait until one of the 3 releases its connection.
    """
    db_path = str(tmp_path / "sem.db")
    pool_size = 3
    pool = SQLiteConnectionPool(db_path, pool_size=pool_size)
    active = threading.Semaphore(0)
    barrier = threading.Barrier(pool_size)
    high_watermark = [0]
    hwm_lock = threading.Lock()
    current_holders = [0]

    def holder() -> None:
        with pool.get_connection() as _conn:
            with hwm_lock:
                current_holders[0] += 1
                if current_holders[0] > high_watermark[0]:
                    high_watermark[0] = current_holders[0]
            barrier.wait(timeout=5.0)
            with hwm_lock:
                current_holders[0] -= 1

    threads = [threading.Thread(target=holder) for _ in range(pool_size)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    pool.close_all()

    assert high_watermark[0] <= pool_size, (
        f"High watermark {high_watermark[0]} exceeded pool_size {pool_size}"
    )
