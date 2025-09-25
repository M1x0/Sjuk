"""SQLite backed persistence for the virtual organization."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional


class Database:
    """Lightweight wrapper around SQLite for storing organization state."""

    def __init__(self, path: str = "data/org.db") -> None:
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._setup()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def _setup(self) -> None:
        with self._lock:
            cursor = self._connection.cursor()
            cursor.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    sender TEXT NOT NULL,
                    sender_role TEXT NOT NULL,
                    recipient TEXT,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    budget REAL,
                    progress REAL NOT NULL DEFAULT 0,
                    owner TEXT,
                    started_at REAL,
                    finished_at REAL,
                    outcome TEXT
                );

                CREATE TABLE IF NOT EXISTS finances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cash REAL NOT NULL,
                    revenue REAL NOT NULL,
                    expenses REAL NOT NULL,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS mistakes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chaos_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    impact TEXT NOT NULL
                );
                """
            )
            self._connection.commit()

    def log_message(
        self,
        sender: str,
        sender_role: str,
        content: str,
        recipient: Optional[str] = None,
        message_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = json.dumps(metadata or {})
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO messages (timestamp, sender, sender_role, recipient, type, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (time.time(), sender, sender_role, recipient, message_type, content, payload),
            )
            self._connection.commit()

    def upsert_agent(self, name: str, role: str, status: str) -> None:
        with self._lock:
            cursor = self._connection.execute(
                "SELECT id FROM agents WHERE name = ?", (name,)
            )
            row = cursor.fetchone()
            if row:
                self._connection.execute(
                    "UPDATE agents SET role = ?, status = ? WHERE id = ?",
                    (role, status, row["id"]),
                )
            else:
                self._connection.execute(
                    "INSERT INTO agents (name, role, status, created_at) VALUES (?, ?, ?, ?)",
                    (name, role, status, time.time()),
                )
            self._connection.commit()

    def record_project(self, project: Dict[str, Any]) -> int:
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO projects (name, category, description, status, budget, progress, owner, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project["name"],
                    project["category"],
                    project["description"],
                    project["status"],
                    project.get("budget"),
                    project.get("progress", 0.0),
                    project.get("owner"),
                    project.get("started_at", time.time()),
                ),
            )
            project_id = cursor.lastrowid
            self._connection.commit()
            return project_id

    def update_project(self, project_id: int, **updates: Any) -> None:
        if not updates:
            return
        columns = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values())
        values.append(project_id)
        with self._lock:
            self._connection.execute(
                f"UPDATE projects SET {columns} WHERE id = ?",
                values,
            )
            self._connection.commit()

    def record_finance(self, cash: float, revenue: float, expenses: float, notes: str = "") -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO finances (timestamp, cash, revenue, expenses, notes) VALUES (?, ?, ?, ?, ?)",
                (time.time(), cash, revenue, expenses, notes),
            )
            self._connection.commit()

    def record_mistake(self, category: str, description: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO mistakes (timestamp, category, description) VALUES (?, ?, ?)",
                (time.time(), category, description),
            )
            self._connection.commit()

    def record_chaos_event(self, event_type: str, impact: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO chaos_events (timestamp, event_type, impact) VALUES (?, ?, ?)",
                (time.time(), event_type, impact),
            )
            self._connection.commit()

    def fetch_agents(self) -> List[Dict[str, Any]]:
        cursor = self._connection.execute(
            "SELECT name, role, status, created_at FROM agents ORDER BY created_at"
        )
        return [dict(row) for row in cursor.fetchall()]

    def fetch_projects(self) -> List[Dict[str, Any]]:
        cursor = self._connection.execute(
            "SELECT * FROM projects ORDER BY started_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def fetch_finance_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self._connection.execute(
            "SELECT * FROM finances ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def fetch_recent_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self._connection.execute(
            "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        rows.reverse()
        for row in rows:
            if row.get("metadata"):
                try:
                    row["metadata"] = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    row["metadata"] = {}
            else:
                row["metadata"] = {}
        return rows

    def fetch_mistakes(self, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self._connection.execute(
            "SELECT * FROM mistakes ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        with self._lock:
            self._connection.close()
