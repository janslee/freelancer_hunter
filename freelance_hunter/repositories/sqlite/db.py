from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str = "freelance_hunter.db") -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            external_id TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            skills_json TEXT NOT NULL,
            currency TEXT,
            budget_min REAL,
            budget_max REAL,
            budget_type TEXT,
            bids_count INTEGER,
            client_name TEXT,
            client_country TEXT,
            client_rating REAL,
            payment_verified INTEGER,
            raw_payload_json TEXT,
            status TEXT NOT NULL DEFAULT 'DISCOVERED',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(platform, external_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            project_key TEXT NOT NULL,
            skill_match_score REAL,
            profit_score REAL,
            clarity_score REAL,
            client_quality_score REAL,
            reusability_score REAL,
            risk_score REAL,
            overall_score REAL,
            confidence REAL,
            decision TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            unknowns_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pricing_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            estimated_hours REAL,
            floor_price REAL,
            suggested_price REAL,
            aggressive_price REAL,
            premium_price REAL,
            currency TEXT,
            strategy TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bid_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            style TEXT NOT NULL,
            headline TEXT NOT NULL,
            body TEXT NOT NULL,
            questions_json TEXT NOT NULL,
            proposed_amount REAL,
            currency TEXT,
            estimated_days INTEGER,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
