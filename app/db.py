from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('policyholder', 'broker'))
);
CREATE TABLE IF NOT EXISTS policies (
    id INTEGER PRIMARY KEY,
    policy_number TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product TEXT NOT NULL,
    status TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    expiration_date TEXT NOT NULL,
    property_address TEXT NOT NULL,
    annual_premium TEXT NOT NULL,
    deductible TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS endorsements (
    id INTEGER PRIMARY KEY,
    policy_id INTEGER NOT NULL REFERENCES policies(id),
    endorsement_number TEXT NOT NULL,
    title TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    limit_value TEXT NOT NULL,
    summary TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)


def seed_demo_data(db_path: Path) -> None:
    initialize_database(db_path)
    with connect(db_path) as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO customers(id, name, email, role) VALUES (?, ?, ?, ?)",
            [
                (1, "Maya Thompson", "maya.demo@example.invalid", "policyholder"),
                (2, "Ravi Patel", "ravi.demo@example.invalid", "broker"),
                (3, "Lena Ortiz", "lena.demo@example.invalid", "policyholder"),
                (4, "Jon Bell", "jon.demo@example.invalid", "policyholder"),
            ],
        )
        connection.execute(
            """INSERT OR IGNORE INTO policies
            (id, policy_number, customer_id, product, status, effective_date, expiration_date,
             property_address, annual_premium, deductible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (1, "POL-4821-AX", 1, "Homeowners Select", "Active", "2025-01-01", "2026-01-01", "18 Hawthorne Lane, Portland, OR", "$2,184.00 / year", "$1,000"),
        )
        connection.execute(
            """INSERT OR IGNORE INTO policies
            (id, policy_number, customer_id, product, status, effective_date, expiration_date,
             property_address, annual_premium, deductible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (2, "POL-7710-QZ", 2, "Commercial Auto Demo", "Active", "2025-04-01", "2026-04-01", "Demo broker account", "$4,820.00 / year", "$2,500"),
        )
        connection.executemany(
            """INSERT OR IGNORE INTO policies
            (id, policy_number, customer_id, product, status, effective_date, expiration_date,
             property_address, annual_premium, deductible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (3, "POL-1193-KM", 3, "Small Business Property Demo", "Active", "2025-02-01", "2026-02-01", "Demo commercial premises", "$3,140.00 / year", "$1,500"),
                (4, "POL-9032-RT", 4, "Homeowners Essentials Demo", "Active", "2025-06-01", "2026-06-01", "Demo residential property", "$1,460.00 / year", "$2,000"),
            ],
        )
        connection.executemany(
            """INSERT OR IGNORE INTO endorsements
            (id, policy_id, endorsement_number, title, effective_date, limit_value, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (1, 1, "04", "Water Backup Endorsement", "2025-08-14", "$10,000", "Demo limit for eligible water backup losses subject to terms and exclusions."),
                (2, 2, "CA-20", "Hired and Non-Owned Auto Liability", "2025-04-01", "$500,000", "Extends liability protection to hired and non-owned autos used in business operations."),
                (3, 3, "BP-14", "Business Income & Extra Expense", "2025-02-01", "$50,000", "Provides actual loss sustained coverage for business interruption with a 72-hour waiting period."),
            ],
        )


def _rows(query: str, parameters: tuple[Any, ...], db_path: Path) -> list[dict[str, Any]]:
    with connect(db_path) as connection:
        return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def find_policy(policy_number: str, db_path: Path) -> dict[str, Any] | None:
    rows = _rows(
        """SELECT p.*, c.name AS customer_name, c.email, c.role FROM policies p
           JOIN customers c ON c.id = p.customer_id WHERE p.policy_number = ?""",
        (policy_number,), db_path,
    )
    return rows[0] if rows else None


def list_endorsements(policy_id: int, db_path: Path) -> list[dict[str, Any]]:
    return _rows("SELECT * FROM endorsements WHERE policy_id = ? ORDER BY effective_date", (policy_id,), db_path)


def list_all_endorsements(db_path: Path) -> list[dict[str, Any]]:
    return _rows(
        """SELECT e.*, p.policy_number, p.product FROM endorsements e
           JOIN policies p ON p.id = e.policy_id ORDER BY e.id""",
        (), db_path,
    )


def search_policies(query: str, db_path: Path) -> list[dict[str, Any]]:
    pattern = f"%{query}%"
    return _rows(
        """SELECT p.policy_number, p.product, p.status, p.effective_date, p.expiration_date, p.deductible, p.annual_premium, c.name AS customer_name, c.role
           FROM policies p JOIN customers c ON c.id = p.customer_id
           WHERE p.policy_number LIKE ? OR c.name LIKE ? OR p.product LIKE ?
           ORDER BY p.policy_number""",
        (pattern, pattern, pattern), db_path,
    )


def list_policies(db_path: Path) -> list[dict[str, Any]]:
    return _rows(
        """SELECT p.id, p.policy_number, p.product, p.status, p.effective_date, p.expiration_date, p.property_address, p.deductible, p.annual_premium, c.name AS customer_name, c.email, c.role
           FROM policies p JOIN customers c ON c.id = p.customer_id
           ORDER BY p.policy_number""",
        (), db_path,
    )

