#!/usr/bin/env python3
"""
Local Embedding Service – Generate vector embeddings on edge devices.

Uses sentence-transformers with a small model (all-MiniLM-L6-v2) for minimal resource usage.
Falls back to keyword hashing if the model is unavailable.

Usage:
    python embedding_service.py --text "User prefers dark mode interfaces"
    python embedding_service.py --text "API integration for payment gateway" --json
    python embedding_service.py --text "Important note" --onnx  # Use ONNX Runtime for speed
"""

import argparse
import base64
import hashlib
import json
import sys


def load_model(model_name: str = "all-MiniLM-L6-v2", use_onnx: bool = False):
    """Load the embedding model. Returns None if unavailable."""
    try:
        if use_onnx:
            from optimum.onnxruntime import ORTModelForFeatureExtraction
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = ORTModelForFeatureExtraction.from_pretrained(model_name, export=True)
            return {"type": "onnx", "tokenizer": tokenizer, "model": model}
        else:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(model_name, device="cpu")
            return {"type": "st", "model": model}
    except ImportError:
        print("Warning: Embedding libraries not installed. Using fallback.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Could not load model: {e}. Using fallback.", file=sys.stderr)
        return None


def generate_embedding(text: str, model_info: dict = None) -> list[float]:
    """Generate embedding vector for text. Falls back to keyword hashing."""
    if model_info is None:
        return _fallback_embedding(text)

    if model_info["type"] == "st":
        import numpy as np
        vec = model_info["model"].encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vec.tolist()
    elif model_info["type"] == "onnx":
        tokenizer = model_info["tokenizer"]
        model = model_info["model"]
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = model(**inputs)
        import torch
        vec = torch.mean(outputs.last_hidden_state, dim=1).detach().numpy().flatten()
        # Normalize
        norm = torch.norm(torch.tensor(vec)).item()
        return (vec / norm).tolist() if norm > 0 else vec.tolist()

    return _fallback_embedding(text)


def _fallback_embedding(text: str, dim: int = 384) -> list[float]:
    """Fallback: Create a deterministic pseudo-embedding from keyword hashing.
    Not semantically meaningful but allows similarity comparisons."""
    import numpy as np
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    # Normalize
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist() if norm > 0 else vec.tolist()


def main():
    parser = argparse.ArgumentParser(description="Generate text embeddings locally.")
    parser.add_argument("--text", required=True, help="Text to embed.")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="Model name or path.")
    parser.add_argument("--onnx", action="store_true", help="Use ONNX Runtime.")
    parser.add_argument("--json", action="store_true", help="Output as JSON.")
    parser.add_argument("--base64", action="store_true", help="Output as base64-encoded bytes.")
    args = parser.parse_args()

    model_info = load_model(args.model, args.onnx)
    embedding = generate_embedding(args.text, model_info)

    if args.base64:
        import numpy as np
        arr = np.array(embedding, dtype=np.float32)
        b64 = base64.b64encode(arr.tobytes()).decode()
        if args.json:
            print(json.dumps({"embedding_b64": b64, "dimensions": len(embedding)}))
        else:
            print(b64)
    elif args.json:
        print(json.dumps({"embedding": embedding, "dimensions": len(embedding)}))
    else:
        # Print compact representation
        sample = embedding[:5]
        print(f"Embedding ({len(embedding)}d): [{', '.join(f'{v:.4f}' for v in sample)}...]")


if __name__ == "__main__":
    main()
