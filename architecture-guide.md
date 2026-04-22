# Architecture Guide: Persistent Memory for Edge Agents

## Storage Backend Options

Choose based on hardware constraints and search requirements:

| Backend | RAM Usage | Search Type | Best For | Setup Complexity |
|---|---|---|---|---|
| **SQLite + sqlite-vss** | ~10-30 MB | Vector + Keyword | General purpose, semantic search | Medium |
| **ChromaDB (local)** | ~50-100 MB | Vector | Pure vector search, easy API | Low |
| **SQLite (plain)** | ~5-10 MB | Keyword only | Minimal RAM, simple setup | Low |
| **LMDB** | ~5-15 MB | Key-value | Ultra-low resource, no search | Low |

### Recommendation: SQLite + sqlite-vss

Best balance of resource efficiency and semantic search capability.

```sql
-- Schema example
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    tags TEXT, -- JSON array as string
    embedding BLOB, -- Vector embedding
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP
);

-- Enable VSS extension for vector search
-- sqlite-vss enables cosine similarity search on embeddings
```

---

## Embedding Model Selection

| Model | Size | Dimensions | Language | Hardware |
|---|---|---|---|---|
| **all-MiniLM-L6-v2** | 22 MB | 384 | Multilingual | CPU, ARM |
| **all-MiniLM-L12-v2** | 33 MB | 384 | Multilingual | CPU, better quality |
| **paraphrase-multilingual-MiniLM** | 118 MB | 384 | Multilingual | CPU, non-English |
| **GTE-small** | 34 MB | 384 | English | CPU, best accuracy |
| **BGE-small-en-v1.5** | 33 MB | 384 | English | CPU, MTEB leaderboard |

### Recommendation for Edge

Use `all-MiniLM-L6-v2` via `sentence-transformers` (Python) or ONNX Runtime for maximum compatibility.

---

## Garbage Collection & Summarization

To prevent unbounded storage growth, implement a background maintenance routine:

### Strategy: Tiered Consolidation

1. **Daily**: Increment `access_count` on reads. Identify cold memories (not accessed in 30 days).
2. **Weekly**: For memories with similar tags/embedding cosine similarity > 0.85, generate a merged summary and delete originals.
3. **Monthly**: Archive very old, low-access memories to compressed storage or delete if below relevance threshold.

### Implementation Sketch

```python
# Pseudocode for GC routine
def run_maintenance():
    # 1. Find similar memories
    clusters = cluster_by_similarity(threshold=0.85)
    for cluster in clusters:
        if len(cluster) > 1:
            summary = llm_summarize([m.content for m in cluster])
            insert_memory(summary, tags=merge_tags(cluster))
            delete_memories(cluster)

    # 2. Decay old memories
    decay_old_memories(days=30, decay_factor=0.9)
```

---

## Integration Patterns

### Pattern A: Direct Function Calls (Recommended for Edge)

The agent framework (e.g., Ollama, llama.cpp) calls local Python functions directly via the tool/function-calling API.

```
[Agent] --(function call)--> [Python Script] --(SQLite)--> [Disk]
```

### Pattern B: REST API Wrapper

A lightweight FastAPI/Flask service provides HTTP endpoints for memory operations. Useful when the agent runtime is separate from the memory backend.

```
[Agent] --(HTTP/JSON)--> [FastAPI Service] --(SQLite)--> [Disk]
```

### Pattern C: Plugin Architecture

Memory operations are implemented as a plugin/module within the agent framework itself (e.g., custom node in a flow-based system).
