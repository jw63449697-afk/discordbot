"""SQLite persistence for contractor contracts."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().with_name("contracts.db")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the contract table and its active-user constraint if needed."""
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_user_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                contract_start_date TEXT NOT NULL,
                contract_created_at TEXT NOT NULL,
                contract_cancelled_at TEXT,
                status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'CANCELLED'))
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_contract_per_user
            ON contracts (discord_user_id)
            WHERE status = 'ACTIVE'
            """
        )


def add_contract(discord_user_id: int, discord_username: str, start_date: str) -> bool:
    """Insert an active contract; return False if the user is already active."""
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        active_contract = connection.execute(
            "SELECT 1 FROM contracts WHERE discord_user_id = ? AND status = 'ACTIVE'",
            (str(discord_user_id),),
        ).fetchone()
        if active_contract is not None:
            return False
        connection.execute(
            """
            INSERT INTO contracts (
                discord_user_id,
                discord_username,
                contract_start_date,
                contract_created_at,
                status
            ) VALUES (?, ?, ?, ?, 'ACTIVE')
            """,
            (str(discord_user_id), discord_username, start_date, created_at),
        )
    return True


def cancel_contract(discord_user_id: int) -> str | None:
    """Cancel the active contract and return its start date, if present."""
    cancelled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        contract = connection.execute(
            """
            SELECT contract_start_date
            FROM contracts
            WHERE discord_user_id = ? AND status = 'ACTIVE'
            """,
            (str(discord_user_id),),
        ).fetchone()
        if contract is None:
            return None
        connection.execute(
            """
            UPDATE contracts
            SET status = 'CANCELLED', contract_cancelled_at = ?
            WHERE discord_user_id = ? AND status = 'ACTIVE'
            """,
            (cancelled_at, str(discord_user_id)),
        )
    return str(contract["contract_start_date"])


def list_active_contracts() -> list[sqlite3.Row]:
    """Return active contracts in a stable, readable order."""
    with _connect() as connection:
        return list(
            connection.execute(
                """
                SELECT discord_user_id, discord_username, contract_start_date
                FROM contracts
                WHERE status = 'ACTIVE'
                ORDER BY contract_start_date ASC, discord_username COLLATE NOCASE ASC, id ASC
                """
            ).fetchall()
        )
