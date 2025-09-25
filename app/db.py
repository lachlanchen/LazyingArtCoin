import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Optional

DB_PATH = os.environ.get("DB_PATH", "data/app.db")

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.execute("PRAGMA foreign_keys=ON;")
    return _conn


@contextmanager
def transaction():
    conn = _connect()
    with _lock:
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def init_db():
    conn = _connect()
    with _lock:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS balances (
                user_id TEXT PRIMARY KEY,
                credits INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS credits_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                delta INTEGER NOT NULL,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS payouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                address TEXT NOT NULL,
                credits INTEGER NOT NULL,
                units TEXT NOT NULL,
                asset TEXT NOT NULL,
                tx_hash TEXT,
                status TEXT NOT NULL,
                idempotency_key TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )


def get_balance(conn: sqlite3.Connection, user_id: str) -> int:
    cur = conn.execute("SELECT credits FROM balances WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return int(row[0]) if row else 0


def ensure_user(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.execute(
        "INSERT OR IGNORE INTO balances(user_id, credits) VALUES(?, 0)", (user_id,)
    )


def add_credits(user_id: str, credits: int, reason: str = "earn") -> int:
    with transaction() as conn:
        ensure_user(conn, user_id)
        conn.execute(
            "INSERT INTO credits_ledger(user_id, delta, reason) VALUES(?,?,?)",
            (user_id, credits, reason),
        )
        conn.execute(
            "UPDATE balances SET credits = credits + ? WHERE user_id = ?",
            (credits, user_id),
        )
        return get_balance(conn, user_id)


def debit_credits_for_payout(
    user_id: str,
    credits: int,
    address: str,
    units: str,
    asset: str,
    idempotency_key: Optional[str],
) -> Dict[str, Any]:
    with transaction() as conn:
        ensure_user(conn, user_id)

        # Idempotency: if key exists, return the existing payout
        if idempotency_key:
            cur = conn.execute(
                "SELECT * FROM payouts WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)

        bal = get_balance(conn, user_id)
        if credits <= 0 or credits > bal:
            raise ValueError("insufficient credits or invalid amount")

        # Create pending payout and reserve credits by debiting immediately
        conn.execute(
            "INSERT INTO credits_ledger(user_id, delta, reason) VALUES(?,?,?)",
            (user_id, -credits, "payout"),
        )
        conn.execute(
            "UPDATE balances SET credits = credits - ? WHERE user_id = ?",
            (credits, user_id),
        )

        conn.execute(
            """
            INSERT INTO payouts(user_id, address, credits, units, asset, status, idempotency_key)
            VALUES(?,?,?,?,?,?,?)
            """,
            (user_id, address, credits, units, asset, "pending", idempotency_key),
        )
        payout_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        cur = conn.execute("SELECT * FROM payouts WHERE id = ?", (payout_id,))
        return dict(cur.fetchone())


def set_payout_sent(payout_id: int, tx_hash: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE payouts SET status = ?, tx_hash = ? WHERE id = ?",
            ("sent", tx_hash, payout_id),
        )


def list_user_payouts(user_id: str) -> Iterable[Dict[str, Any]]:
    conn = _connect()
    with _lock:
        cur = conn.execute(
            "SELECT * FROM payouts WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        for row in cur.fetchall():
            yield dict(row)


def get_setting(key: str) -> Optional[str]:
    init_db()
    conn = _connect()
    with _lock:
        cur = conn.execute("SELECT value FROM app_config WHERE key = ?", (key,))
        row = cur.fetchone()
        if row is None:
            return None
        value = row[0]
        return str(value) if value is not None else None


def set_setting(key: str, value: Optional[str]) -> None:
    normalized = value.strip() if isinstance(value, str) else value
    init_db()
    with transaction() as conn:
        if not normalized:
            conn.execute("DELETE FROM app_config WHERE key = ?", (key,))
        else:
            conn.execute(
                """
                INSERT INTO app_config(key, value)
                VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, normalized),
            )


def list_settings(prefix: Optional[str] = None) -> Dict[str, str]:
    init_db()
    conn = _connect()
    with _lock:
        if prefix:
            cur = conn.execute(
                "SELECT key, value FROM app_config WHERE key LIKE ? ORDER BY key",
                (f"{prefix}%",),
            )
        else:
            cur = conn.execute("SELECT key, value FROM app_config ORDER BY key")
        return {row[0]: row[1] for row in cur.fetchall()}
