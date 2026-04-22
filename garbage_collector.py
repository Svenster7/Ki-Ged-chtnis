#!/usr/bin/env python3
"""
Memory Maintenance & Garbage Collector – Keep the agent's memory lean.

Consolidates similar memories, decays old entries, and prevents unbounded growth.

Usage:
    python garbage_collector.py --db ./memory.db --dry-run
    python garbage_collector.py --db ./memory.db --similarity-threshold 0.85
    python garbage_collector.py --db ./memory.db --decay-days 30 --consolidate
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path


def find_similar_memories(conn: sqlite3.Connection, threshold: float) -> list[list[dict]]:
    """Find clusters of memories with similar content using simple word overlap.
    For production, use embedding cosine similarity."""
    rows = conn.execute(
        "SELECT id, content, tags, embedding FROM memories WHERE embedding IS NOT NULL"
    ).fetchall()

    memories = [{"id": r[0], "content": r[1], "tags": json.loads(r[2]), "embedding": r[3]} for r in rows]

    import numpy as np
    clusters = []
    visited = set()

    for mem in memories:
        if mem["id"] in visited:
            continue
        cluster = [mem]
        visited.add(mem["id"])
        mem_vec = np.frombuffer(mem["embedding"], dtype=np.float32) if mem["embedding"] else None

        if mem_vec is not None:
            for other in memories:
                if other["id"] in visited or other["embedding"] is None:
                    continue
                other_vec = np.frombuffer(other["embedding"], dtype=np.float32)
                sim = np.dot(mem_vec, other_vec) / (np.linalg.norm(mem_vec) * np.linalg.norm(other_vec))
                if sim >= threshold:
                    cluster.append(other)
                    visited.add(other["id"])

        if len(cluster) > 1:
            clusters.append(cluster)

    return clusters


def consolidate_cluster(conn: sqlite3.Connection, cluster: list[dict]) -> int:
    """Merge a cluster of similar memories into a single summary entry."""
    # Simple merge: concatenate and mark as consolidated
    combined_content = " | ".join(m["content"][:200] for m in cluster)
    all_tags = list(set(tag for m in cluster for tag in m["tags"]))

    cursor = conn.execute(
        "INSERT INTO memories (content, tags) VALUES (?, ?)",
        (f"[Consolidated] {combined_content}", json.dumps(all_tags[:5]))
    )
    new_id = cursor.lastrowid

    # Delete old memories
    for mem in cluster:
        conn.execute("DELETE FROM memories WHERE id = ?", (mem["id"],))

    conn.commit()
    return new_id


def decay_old_memories(conn: sqlite3.Connection, days: int, decay_factor: float = 0.9):
    """Reduce relevance of old, rarely accessed memories."""
    cutoff = datetime.now() - timedelta(days=days)
    conn.execute(
        """
        UPDATE memories
        SET access_count = CAST(access_count * ? AS INTEGER)
        WHERE last_accessed < ? AND access_count > 0
        """,
        (decay_factor, cutoff.isoformat())
    )
    conn.commit()


def run_maintenance(db_path: str, similarity_threshold: float, decay_days: int,
                    consolidate: bool = True, dry_run: bool = False) -> dict:
    """Run full maintenance cycle. Returns statistics."""
    conn = sqlite3.connect(db_path)
    stats = {"consolidated": 0, "decayed": 0, "deleted": 0}

    try:
        if consolidate:
            clusters = find_similar_memories(conn, similarity_threshold)
            if dry_run:
                print(f"[DRY-RUN] Would consolidate {len(clusters)} clusters:")
                for i, cluster in enumerate(clusters):
                    print(f"  Cluster {i+1}: {len(cluster)} memories -> IDs: {[m['id'] for m in cluster]}")
            else:
                for cluster in clusters:
                    new_id = consolidate_cluster(conn, cluster)
                    stats["consolidated"] += len(cluster)
                    stats["deleted"] += len(cluster) - 1
                    print(f"Consolidated {len(cluster)} memories into ID {new_id}")

        if decay_days > 0:
            if dry_run:
                print(f"[DRY-RUN] Would decay memories older than {decay_days} days")
            else:
                decay_old_memories(conn, decay_days)
                stats["decayed"] = conn.total_changes
                print(f"Decayed old memories (factor: 0.9)")

    finally:
        conn.close()

    return stats


def main():
    parser = argparse.ArgumentParser(description="Memory garbage collector and maintenance.")
    parser.add_argument("--db", required=True, help="Path to memory database.")
    parser.add_argument("--similarity-threshold", type=float, default=0.85,
                        help="Cosine similarity threshold for consolidation (0.0-1.0).")
    parser.add_argument("--decay-days", type=int, default=30,
                        help="Decay memories older than N days (0 to disable).")
    parser.add_argument("--consolidate", action="store_true", help="Enable memory consolidation.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying.")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"Error: Database {args.db} not found.", file=sys.stderr)
        sys.exit(1)

    stats = run_maintenance(
        args.db,
        args.similarity_threshold,
        args.decay_days,
        args.consolidate,
        args.dry_run
    )

    print(f"\nMaintenance complete: {stats}")


if __name__ == "__main__":
    main()
