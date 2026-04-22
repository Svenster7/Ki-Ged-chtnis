#!/usr/bin/env python3
"""
Core Memory Manager – Fast, always-in-context key-value store.

Usage:
    python core_memory.py --action append --key user_name --value "Alice"
    python core_memory.py --action get --key user_name
    python core_memory.py --action list
    python core_memory.py --action delete --key old_preference
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS core_memory (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def append(db_path: str, key: str, value: str) -> None:
    conn = init_db(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO core_memory (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value)
    )
    conn.commit()
    conn.close()
    print(f"Core memory set: {key} = {value}")


def get(db_path: str, key: str) -> str | None:
    conn = init_db(db_path)
    row = conn.execute("SELECT value FROM core_memory WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        print(row[0])
        return row[0]
    print(f"Key '{key}' not found in core memory.", file=sys.stderr)
    return None


def list_all(db_path: str) -> dict[str, str]:
    conn = init_db(db_path)
    rows = conn.execute("SELECT key, value FROM core_memory ORDER BY key").fetchall()
    conn.close()
    result = {k: v for k, v in rows}
    print(json.dumps(result, indent=2))
    return result


def delete(db_path: str, key: str) -> None:
    conn = init_db(db_path)
    cursor = conn.execute("DELETE FROM core_memory WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    if cursor.rowcount > 0:
        print(f"Deleted key: {key}")
    else:
        print(f"Key '{key}' not found.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Manage core memory entries.")
    parser.add_argument("--action", required=True, choices=["append", "replace", "get", "list", "delete"])
    parser.add_argument("--key", default=None, help="Memory key.")
    parser.add_argument("--value", default=None, help="Memory value.")
    parser.add_argument("--db", default="./core_memory.db", help="Path to core memory database.")
    args = parser.parse_args()

    if args.action in ("append", "replace"):
        if not args.key or not args.value:
            print("Error: --key and --value required for append/replace.", file=sys.stderr)
            sys.exit(1)
        append(args.db, args.key, args.value)
    elif args.action == "get":
        if not args.key:
            print("Error: --key required for get.", file=sys.stderr)
            sys.exit(1)
        get(args.db, args.key)
    elif args.action == "list":
        list_all(args.db)
    elif args.action == "delete":
        if not args.key:
            print("Error: --key required for delete.", file=sys.stderr)
            sys.exit(1)
        delete(args.db, args.key)


if __name__ == "__main__":
    main()
