#!/usr/bin/env python3
"""
Archival Memory Search – Retrieve memories for edge agents.

Supports keyword search via FTS5 and (optionally) semantic search via embeddings.

Usage:
    python memory_search.py --query "dark mode preference" --db ./memory.db --top-k 5
    python memory_search.py --query "API key" --db ./memory.db --top-k 3 --json
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def search_keyword(db_path: str, query: str, top_k: int = 5) -> list[dict]:
    """Search memories using FTS5 keyword search."""
    conn = sqlite3.connect(db_path)
    # Update access stats
    results = conn.execute(
        """
        SELECT m.id, m.content, m.tags, m.created_at, m.access_count
        FROM memories_fts f
        JOIN memories m ON m.id = f.rowid
        WHERE memories_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, top_k)
    ).fetchall()

    memories = []
    for row in results:
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = datetime('now') WHERE id = ?",
            (row[0],)
        )
        memories.append({
            "id": row[0],
            "content": row[1],
            "tags": json.loads(row[2]),
            "created_at": row[3],
            "access_count": row[4] + 1
        })
    conn.commit()
    conn.close()
    return memories


def search_all(db_path: str, query: str, top_k: int = 5) -> list[dict]:
    """Fallback search across all content if FTS5 not available."""
    conn = sqlite3.connect(db_path)
    results = conn.execute(
        """
        SELECT id, content, tags, created_at, access_count
        FROM memories
        WHERE content LIKE ? OR tags LIKE ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (f"%{query}%", f"%{query}%", top_k)
    ).fetchall()

    memories = []
    for row in results:
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = datetime('now') WHERE id = ?",
            (row[0],)
        )
        memories.append({
            "id": row[0],
            "content": row[1],
            "tags": json.loads(row[2]),
            "created_at": row[3],
            "access_count": row[4] + 1
        })
    conn.commit()
    conn.close()
    return memories


def search_semantic(db_path: str, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Semantic search using cosine similarity on embeddings.
    Requires sqlite-vss extension or manual similarity computation."""
    conn = sqlite3.connect(db_path)
    # Fallback: fetch all and compute cosine similarity in Python
    # For production, use sqlite-vss extension for native vector search
    import numpy as np

    query_vec = np.array(query_embedding, dtype=np.float32)
    rows = conn.execute("SELECT id, content, tags, embedding, created_at, access_count FROM memories WHERE embedding IS NOT NULL").fetchall()

    similarities = []
    for row in rows:
        if row[3] is None:
            continue
        mem_vec = np.frombuffer(row[3], dtype=np.float32)
        # Cosine similarity
        sim = np.dot(query_vec, mem_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(mem_vec))
        similarities.append((sim, row))

    similarities.sort(reverse=True, key=lambda x: x[0])

    memories = []
    for sim, row in similarities[:top_k]:
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = datetime('now') WHERE id = ?",
            (row[0],)
        )
        memories.append({
            "id": row[0],
            "content": row[1],
            "tags": json.loads(row[2]),
            "similarity": float(sim),
            "created_at": row[4],
            "access_count": row[5] + 1
        })
    conn.commit()
    conn.close()
    return memories


def main():
    parser = argparse.ArgumentParser(description="Search the agent's archival memory.")
    parser.add_argument("--query", required=True, help="Search query.")
    parser.add_argument("--db", default="./agent_memory.db", help="Path to SQLite database file.")
    parser.add_argument("--top-k", type=int, default=5, help="Maximum number of results.")
    parser.add_argument("--json", action="store_true", help="Output results as JSON.")
    parser.add_argument("--semantic", action="store_true", help="Use semantic search (requires embeddings).")
    parser.add_argument("--embedding", default=None, help="Query embedding as JSON array (for semantic search).")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"Error: Database {args.db} not found.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.semantic and args.embedding:
            query_embedding = json.loads(args.embedding)
            memories = search_semantic(args.db, query_embedding, args.top_k)
        else:
            try:
                memories = search_keyword(args.db, args.query, args.top_k)
            except sqlite3.OperationalError:
                # FTS5 not available, fallback
                memories = search_all(args.db, args.query, args.top_k)
    except Exception as e:
        print(f"Error during search: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(memories, indent=2, default=str))
    else:
        for mem in memories:
            print(f"[ID:{mem['id']}] {mem['content'][:120]}... (accessed: {mem['access_count']}x)")


if __name__ == "__main__":
    main()
