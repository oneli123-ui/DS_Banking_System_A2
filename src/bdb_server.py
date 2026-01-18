#!/usr/bin/env python3
"""
Bank Database Server (BDB)
Phase 2 - Three-tier architecture
Manages SQLite database and provides RPC interface for BAS
"""

import sqlite3
import os
import hashlib
import Pyro5.api
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
import time

from common import money

DATABASE_FILE = "banking.db"


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@Pyro5.api.expose
class BankDatabaseServer:
    """
    Phase 2 BDB Server (Database Tier)
    - Manages SQLite database for persistent storage
    - Provides RPC interface for BAS server only
    - No direct access from BC client
    """

    def __init__(self):
        """Initialize database and create tables if needed."""
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with required tables."""
        with get_db() as conn:
            cursor = conn.cursor()

            # Users table: stores user credentials
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    created_at INTEGER
                )
            """)

            # Accounts table: stores account information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    username TEXT PRIMARY KEY,
                    balance TEXT NOT NULL,
                    created_at INTEGER,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
            """)

            # Transfers table: stores transfer records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transfers (
                    transfer_id TEXT PRIMARY KEY,
                    from_user TEXT NOT NULL,
                    to_user TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    fee TEXT NOT NULL,
                    reference TEXT,
                    status TEXT NOT NULL,
                    reason TEXT,
                    created_at INTEGER,
                    updated_at INTEGER,
                    FOREIGN KEY (from_user) REFERENCES accounts(username),
                    FOREIGN KEY (to_user) REFERENCES accounts(username)
                )
            """)

            # Audit logs table: stores all operations for audit trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    username TEXT,
                    details TEXT,
                    timestamp INTEGER
                )
            """)

            conn.commit()

            # Initialize mock users if they don't exist
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                self._init_mock_users()

    def _init_mock_users(self):
        """Initialize with mock users for testing."""
        mock_users = {
            "alice": "alice123",
            "bob": "bob123",
        }
        mock_balances = {
            "alice": "50000.00",
            "bob": "1000.00",
        }

        with get_db() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())

            for username, password in mock_users.items():
                # Hash password (simple hash for demo)
                pwd_hash = hashlib.sha256(password.encode()).hexdigest()

                # Insert user
                cursor.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, pwd_hash, current_time),
                )

                # Insert account
                cursor.execute(
                    "INSERT INTO accounts (username, balance, created_at) VALUES (?, ?, ?)",
                    (username, mock_balances[username], current_time),
                )

                # Log
                cursor.execute(
                    "INSERT INTO audit_logs (operation, username, details, timestamp) VALUES (?, ?, ?, ?)",
                    ("USER_CREATED", username, "Mock user initialized", current_time),
                )

            conn.commit()

    # ---------- User operations ----------

    def get_user(self, username: str) -> Dict[str, Any]:
        """Get user record."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()

            if row:
                return {
                    "username": row["username"],
                    "email": row["email"],
                    "created_at": row["created_at"],
                }
            return {}

    def verify_user(self, username: str, password: str) -> bool:
        """Verify user credentials."""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password_hash FROM users WHERE username = ?", (username,)
            )
            row = cursor.fetchone()

            if row and row["password_hash"] == pwd_hash:
                # Log login attempt
                cursor.execute(
                    "INSERT INTO audit_logs (operation, username, timestamp) VALUES (?, ?, ?)",
                    ("LOGIN_SUCCESS", username, int(time.time())),
                )
                conn.commit()
                return True

            # Log failed login
            if username:  # Only log if username was provided
                cursor.execute(
                    "INSERT INTO audit_logs (operation, username, timestamp) VALUES (?, ?, ?)",
                    ("LOGIN_FAILED", username, int(time.time())),
                )
                conn.commit()
            return False

    def create_user(self, username: str, password: str, email: str = "") -> bool:
        """Create a new user."""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        current_time = int(time.time())

        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)",
                    (username, pwd_hash, email, current_time),
                )

                # Create associated account
                cursor.execute(
                    "INSERT INTO accounts (username, balance, created_at) VALUES (?, ?, ?)",
                    (username, "0.00", current_time),
                )

                # Log
                cursor.execute(
                    "INSERT INTO audit_logs (operation, username, details, timestamp) VALUES (?, ?, ?, ?)",
                    ("USER_CREATED", username, f"Email: {email}", current_time),
                )

                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # User already exists

    # ---------- Account/Balance operations ----------

    def get_balance(self, username: str) -> Optional[str]:
        """Get account balance for user."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM accounts WHERE username = ?", (username,))
            row = cursor.fetchone()

            if row:
                return row["balance"]
            return None

    def update_balance(self, username: str, new_balance: str) -> bool:
        """Update account balance for user."""
        new_balance = str(money(new_balance))  # Ensure proper decimal formatting
        current_time = int(time.time())

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE username = ?",
                (new_balance, username),
            )

            # Log balance change
            cursor.execute(
                "INSERT INTO audit_logs (operation, username, details, timestamp) VALUES (?, ?, ?, ?)",
                (
                    "BALANCE_UPDATED",
                    username,
                    f"New balance: {new_balance}",
                    current_time,
                ),
            )

            conn.commit()
            return cursor.rowcount > 0

    # ---------- Transfer operations ----------

    def create_transfer(self, transfer_record: Dict[str, Any]) -> bool:
        """Create a transfer record."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO transfers 
                    (transfer_id, from_user, to_user, amount, fee, reference, status, reason, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        transfer_record["transfer_id"],
                        transfer_record["from"],
                        transfer_record["to"],
                        transfer_record["amount"],
                        transfer_record["fee"],
                        transfer_record.get("reference", ""),
                        transfer_record["status"],
                        transfer_record.get("reason", ""),
                        transfer_record["created_at"],
                        transfer_record["updated_at"],
                    ),
                )

                # Log transfer
                cursor.execute(
                    "INSERT INTO audit_logs (operation, username, details, timestamp) VALUES (?, ?, ?, ?)",
                    (
                        "TRANSFER_CREATED",
                        transfer_record["from"],
                        f"Transfer {transfer_record['transfer_id']} to {transfer_record['to']}: ${transfer_record['amount']}",
                        int(time.time()),
                    ),
                )

                conn.commit()
                return True
        except Exception:
            return False

    def get_transfer(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get transfer record by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transfers WHERE transfer_id = ?", (transfer_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "transfer_id": row["transfer_id"],
                    "from": row["from_user"],
                    "to": row["to_user"],
                    "amount": row["amount"],
                    "fee": row["fee"],
                    "reference": row["reference"],
                    "status": row["status"],
                    "reason": row["reason"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            return None

    def update_transfer(self, transfer_id: str, status: str, reason: str = "") -> bool:
        """Update transfer status."""
        current_time = int(time.time())

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE transfers SET status = ?, reason = ?, updated_at = ? WHERE transfer_id = ?",
                (status, reason, current_time, transfer_id),
            )

            # Log update
            cursor.execute(
                "INSERT INTO audit_logs (operation, username, details, timestamp) VALUES (?, ?, ?, ?)",
                ("TRANSFER_UPDATED", "", f"Transfer {transfer_id} status: {status}", current_time),
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_transfers_by_user(self, username: str) -> List[Dict[str, Any]]:
        """Get all transfers for a user (both sent and received)."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM transfers WHERE from_user = ? OR to_user = ? ORDER BY created_at DESC",
                (username, username),
            )
            rows = cursor.fetchall()

            return [
                {
                    "transfer_id": row["transfer_id"],
                    "from": row["from_user"],
                    "to": row["to_user"],
                    "amount": row["amount"],
                    "fee": row["fee"],
                    "reference": row["reference"],
                    "status": row["status"],
                    "reason": row["reason"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    # ---------- Audit operations ----------

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit logs."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()

            return [
                {
                    "log_id": row["log_id"],
                    "operation": row["operation"],
                    "username": row["username"],
                    "details": row["details"],
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]

    def health_check(self) -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "database": DATABASE_FILE}


def main():
    """Start BDB daemon + register server object."""
    # Remove old database for fresh start (optional, comment out for persistence)
    # if os.path.exists(DATABASE_FILE):
    #     os.remove(DATABASE_FILE)

    daemon = Pyro5.api.Daemon(host="127.0.0.1", port=9091)
    uri = daemon.register(BankDatabaseServer(), objectId="BDB")

    print("BDB server running.")
    print("URI:", uri)
    print("Object name: BDB")
    print("Database file:", DATABASE_FILE)
    print("Keep this terminal open.")
    daemon.requestLoop()


if __name__ == "__main__":
    main()
