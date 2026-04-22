---
name: edge-agent-memory
description: Design and implement persistent tiered-memory systems for local edge-running AI agents. Use when creating or configuring local agents (e.g., Gemma, Llama, Mistral running via Ollama, LM Studio, or Google AI Edge Gallery) that require long-term memory beyond their context window. Covers MemGPT-style two-tier memory (core + archival), tool definitions for memory operations, SQLite/ChromaDB storage backends, embedding models for semantic search, and garbage collection strategies. Triggers on requests involving local agent memory, edge AI persistence, context-window extension, MemGPT implementation, or agent long-term memory architecture.
---

# Edge Agent Memory

Build persistent, resource-efficient memory systems for local edge agents using tiered storage (Core + Archival), vector search, and automated maintenance.

## Workflow

1. **Choose architecture** → Read [references/architecture-guide.md](references/architecture-guide.md)
2. **Generate system prompt** → Read [references/system-prompt-template.md](references/system-prompt-template.md)
3. **Define tools** → Read [references/tool-definitions.md](references/tool-definitions.md)
4. **Implement storage** → Use scripts in `scripts/`
5. **Configure maintenance** → Use garbage collector script

---

## Step 1: Architecture Selection

Read [references/architecture-guide.md](references/architecture-guide.md) to select the storage backend and integration pattern based on hardware constraints.

**Quick decision matrix:**

| Constraint | Choice |
|---|---|
| < 100 MB RAM available | SQLite plain + keyword search |
| 100-500 MB RAM available | SQLite + sqlite-vss |
| Vector search required | ChromaDB local or sqlite-vss |
| Minimal setup | SQLite plain |
| Existing HTTP stack | REST API wrapper pattern |

---

## Step 2: System Prompt Generation

Read [references/system-prompt-template.md](references/system-prompt-template.md) for the full template.

**Key customization points:**
- Replace `[NAME/DESCRIPTION]` with agent identity
- Replace `[DEVICE/PLATFORM]` with target hardware
- Adjust tool function names to match implementation
- Keep rules section strict – this enforces pro-active memory usage

**Critical rules to include:**
1. Proactive search before answering on vaguely familiar topics
2. Dense summaries before session end
3. No hallucination about past conversations – search or admit ignorance
4. Tag every archival insert with 3-5 keywords

---

## Step 3: Tool Definitions

Read [references/tool-definitions.md](references/tool-definitions.md) for complete JSON schemas.

**Required tools:**
- `core_memory_append(key, value)` – Always-in-context facts
- `archival_memory_insert(content, tags)` – Long-term storage
- `archival_memory_search(query, top_k)` – Retrieval

**Optional tools:**
- `core_memory_replace(key, value)` – Update existing core facts
- `conversation_summarize(session_id, summary)` – Auto-summarize on session end

Register these as function definitions in the agent framework (Ollama, LM Studio, Google AI Edge Gallery, etc.).

---

## Step 4: Storage Implementation

Use the provided scripts. All support `--db <path>` for custom database location.

### Core Memory (Fast Key-Value)

```bash
# Set a core fact
python scripts/core_memory.py --action append --key user_name --value "Alice" --db ./core.db

# Retrieve
python scripts/core_memory.py --action get --key user_name --db ./core.db

# List all
python scripts/core_memory.py --action list --db ./core.db
```

### Archival Memory (Searchable Storage)

```bash
# Store a memory
python scripts/memory_store.py --content "User prefers dark mode" --tags '["preferences","ui"]' --db ./memory.db

# Generate embedding (optional, for semantic search)
EMBEDDING=$(python scripts/embedding_service.py --text "User prefers dark mode" --base64 --json | jq -r '.embedding_b64')

# Store with embedding
python scripts/memory_store.py --content "User prefers dark mode" --tags '["preferences","ui"]' --db ./memory.db --embedding "$EMBEDDING"

# Search
python scripts/memory_search.py --query "dark mode" --db ./memory.db --top-k 5 --json
```

### Embeddings

```bash
# Standard (sentence-transformers)
python scripts/embedding_service.py --text "API integration" --json

# ONNX Runtime (faster)
python scripts/embedding_service.py --text "API integration" --onnx --json

# Fallback (no dependencies)
python scripts/embedding_service.py --text "API integration" --json  # auto-falls back
```

---

## Step 5: Maintenance (Garbage Collection)

Prevent unbounded growth with periodic consolidation:

```bash
# Preview what would be consolidated
python scripts/garbage_collector.py --db ./memory.db --dry-run --consolidate

# Run consolidation and decay
python scripts/garbage_collector.py --db ./memory.db --consolidate --decay-days 30

# Adjust similarity threshold (default 0.85)
python scripts/garbage_collector.py --db ./memory.db --consolidate --similarity-threshold 0.75
```

**Recommended schedule:** Run weekly via cron/systemd timer on edge devices.

---

## Resource Budget Reference

| Component | Disk | RAM | Notes |
|---|---|---|---|
| SQLite database | ~10-50 KB per memory | Negligible | Grows linearly |
| all-MiniLM-L6-v2 | 22 MB download | ~30-50 MB | One-time load |
| ChromaDB | ~50-100 KB per memory | ~50-100 MB | Higher baseline |
| Embedding generation | None | ~10-20 MB spike | Temporary |
| GC routine | None | ~10-20 MB | During run only |

---

## Integration Example: Ollama Tool

```python
# tools.py - Register with Ollama's tool support
import subprocess

def archival_memory_insert(content: str, tags: list[str]) -> str:
    result = subprocess.run(
        ["python", "scripts/memory_store.py", "--content", content,
         "--tags", json.dumps(tags), "--db", "./memory.db"],
        capture_output=True, text=True
    )
    return result.stdout

def archival_memory_search(query: str, top_k: int = 5) -> str:
    result = subprocess.run(
        ["python", "scripts/memory_search.py", "--query", query,
         "--top-k", str(top_k), "--db", "./memory.db", "--json"],
        capture_output=True, text=True
    )
    return result.stdout
```
