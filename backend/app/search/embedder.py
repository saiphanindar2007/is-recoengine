"""
Lazy-loads a sentence-transformer model for dense semantic embeddings.

Deliberately NOT a hard dependency: `sentence-transformers` (and its torch
dependency) live in the optional `requirements-embeddings.txt`, not the core
`requirements.txt` — installing it pulls PyPI's default CUDA-enabled torch
wheel (over a gigabyte) unless the CPU-only wheel is installed first (see
requirements-embeddings.txt for the exact command). Keeping this out of the
default install means the free-tier core deployment stays small and fast to
cold-start; a deployment that wants real dense semantic search opts in
explicitly.

EMBEDDING_MODE=tfidf_only skips even attempting the import — used by CI/tests
so the suite stays deterministic and never needs the heavy dependency
installed at all.
"""
import os
import logging

logger = logging.getLogger("is_reco.matching_engine")

EMBEDDING_MODE = os.environ.get("EMBEDDING_MODE", "hybrid")  # "hybrid" | "tfidf_only"
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

_model = None
_load_attempted = False


def try_load_embedder():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    if EMBEDDING_MODE == "tfidf_only":
        logger.info("EMBEDDING_MODE=tfidf_only - dense embeddings disabled by config.")
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info(f"Loaded sentence-transformer model '{EMBEDDING_MODEL_NAME}' for hybrid semantic search.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"Could not load sentence-transformer model ({exc}). "
            "Falling back to TF-IDF-only matching. Set EMBEDDING_MODE=tfidf_only to silence this."
        )
        _model = None
    return _model
