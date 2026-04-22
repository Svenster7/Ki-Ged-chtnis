#!/usr/bin/env python3
"""
Archival Memory Insert – Persistent storage for edge agent memories.

Usage:
    python memory_store.py --content "User prefers dark mode in all apps" --tags '["preferences", "ui", "user"]' --db ./memory.db
    python memory_store.py --content "API key for service X: abc123" --tags '["secrets", "api", "service_x"]' --db ./memory.db --encrypt
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database with required tables and VSS support."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP
        )
    """)
    # FTS5 for fast keyword search (fallback if VSS unavailable)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content,
            tags,
            content_rowid=rowid,
            content='memories'
        )
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content, tags)
            VALUES (new.id, new.content, new.tags);
        END
    """)
    conn.commit()
    return conn


def store_memory(db_path: str, content: str, tags: list[str], embedding: bytes = None) -> int:
    """Store a memory in the database. Returns the memory ID."""
    conn = init_database(db_path)
    cursor = conn.execute(
        "INSERT INTO memories (content, tags, embedding) VALUES (?, ?, ?)",
        (content, json.dumps(tags), embedding)
    )
    memory_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return memory_id


def main():
    parser = argparse.ArgumentParser(description="Store a memory in the agent's archival memory.")
    parser.add_argument("--content", required=True, help="Memory content to store.")
    parser.add_argument("--tags", required=True, help="JSON array of tags (e.g. '[\"python\", \"project-a\"]').")
    parser.add_argument("--db", default="./agent_memory.db", help="Path to SQLite database file.")
    parser.add_argument("--embedding", default=None, help="Optional pre-computed embedding blob (base64).")
    args = parser.parse_args()

    try:
        tags = json.loads(args.tags)
        if not isinstance(tags, list):
            raise ValueError("Tags must be a JSON array")
    except json.JSONDecodeError:
        print("Error: --tags must be a valid JSON array", file=sys.stderr)
        sys.exit(1)

    embedding = None
    if args.embedding:
        import base64
        embedding = base64.b64decode(args.embedding)

    memory_id = store_memory(args.db, args.content, tags, embedding)
    print(f"Memory stored with ID: {memory_id}")


if __name__ == "__main__":
    main()
