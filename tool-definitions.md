# Tool Definitions (Function Calling Schema)

## Schema for Agent Memory Tools

Provide these function definitions to the agent framework (e.g., Google AI Edge Gallery, Ollama, LM Studio) so the model can invoke them autonomously.

---

## Core Memory Tools

### core_memory_append

```json
{
  "name": "core_memory_append",
  "description": "Fuegt dem Core Memory essenzielle, immer-im-Kontext Fakten hinzu. Selektiv nutzen – nur fuer kritische User-Info und aktive Direktiven.",
  "parameters": {
    "type": "object",
    "properties": {
      "key": {
        "type": "string",
        "description": "Kategorischer Schluessel (z.B. 'user_name', 'active_project', 'coding_style')."
      },
      "value": {
        "type": "string",
        "description": "Der konkrete Wert/Eintrag. Maximal 200 Zeichen."
      }
    },
    "required": ["key", "value"]
  }
}
```

### core_memory_replace

```json
{
  "name": "core_memory_replace",
  "description": "Ersetzt einen bestehenden Core-Memory-Eintrag. Nutzen wenn sich ein Fakt aendert (z.B. neuer Projektname).",
  "parameters": {
    "type": "object",
    "properties": {
      "key": {
        "type": "string",
        "description": "Der zu aendernde Schluessel."
      },
      "value": {
        "type": "string",
        "description": "Der neue Wert. Maximal 200 Zeichen."
      }
    },
    "required": ["key", "value"]
  }
}
```

---

## Archival Memory Tools

### archival_memory_insert

```json
{
  "name": "archival_memory_insert",
  "description": "Speichert Informationen dauerhaft und ressourcenschonend im lokalen Langzeitgedaechtnis. Nur fuer dichte, informative Inhalte – keine Füllwoerter.",
  "parameters": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "Die zu speichernde Information. Mache sie praezise, dicht und reich an Keywords, um sie spaeter gut wiederzufinden."
      },
      "tags": {
        "type": "array",
        "items": { "type": "string" },
        "description": "3-5 Keywords zur Kategorisierung (z.B. ['Python', 'Privat', 'Projekt_X'])."
      }
    },
    "required": ["content", "tags"]
  }
}
```

### archival_memory_search

```json
{
  "name": "archival_memory_search",
  "description": "Durchsucht das unendliche lokale Gedaechtnis nach vergangenen Informationen. Immer nutzen wenn der Kontext unvollstaendig erscheint.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Der Suchbegriff oder die Frage an das Gedaechtnis. Kann Stichwoerter oder eine vollstaendige Frage sein."
      },
      "top_k": {
        "type": "integer",
        "description": "Maximale Anzahl Ergebnisse (Default: 5).",
        "default": 5
      }
    },
    "required": ["query"]
  }
}
```

---

## Optional: Conversation Summary Tool

### conversation_summarize

```json
{
  "name": "conversation_summarize",
  "description": "Wird automatisch aufgerufen wenn eine Session endet. Erzeugt eine extrem kompakte Zusammenfassung aller wichtigen Fakten und speichert sie.",
  "parameters": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "Eindeutige Session-ID."
      },
      "summary": {
        "type": "string",
        "description": "Dichte Zusammenfassung. Jeder Satz muss Informationstragend sein."
      }
    },
    "required": ["session_id", "summary"]
  }
}
```
