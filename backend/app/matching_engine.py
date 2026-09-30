"""
Backward-compatible facade over `app/search/` — the hybrid matching engine
was refactored from one 320-line module of loose globals/functions into a
proper layered package (preprocessing, lexical index, vector index,
embedder, ranking, graph traversal, orchestrating engine — see
`app/search/engine.py` for the composition). This module exists so every
existing caller (`routers/recommend_router.py`, `routers/standards_router.py`,
`routers/analytics_router.py`, `evaluation.py`, `main.py`, and the test
suite) keeps working against exactly the same names, without needing to
change a single import — `from . import matching_engine` and
`matching_engine.<anything>` behave identically to before the refactor.

What changed under the hood (see `app/search/` for the full rationale in
each module's docstring):
  - domain-aware preprocessing: lemmatization + procurement synonym/
    spelling-variant expansion, applied to both queries and the indexed
    corpus (`search/preprocessing.py`)
  - a real precomputed vector index for embedding search, not a
    recompute-every-query similarity call (`search/vector_index.py`)
  - a genuine multi-feature reranking stage — exact IS-number identifier
    matching, currency/verification/certification-aware adjustments — on
    top of the lexical+semantic blend (`search/ranking.py`)
  - query-side exact identifier short-circuit boosting, so typing an exact
    IS number is treated as an unambiguous request, not just one more
    similarity signal (`search/identifiers.py`)

None of this changes the wire format: `semantic_search()` still returns
`(results, normalized_query, detected_script, embeddings_used)` with
`results` as `[(standard, score, matched_terms, score_breakdown), ...]`,
and `expand_related()` still returns `[{"standard": ..., "relations": [...]}]`.
"""
from typing import Optional

from .search.engine import engine as _engine
from .search.preprocessing import normalize_query  # noqa: F401 - re-exported for API completeness
from .search.ranking import (  # noqa: F401
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    confidence_tier,
    evidence_snippet_for,
)


def rebuild_index(db) -> None:
    _engine.rebuild_index(db)


def is_index_ready() -> bool:
    return _engine.is_index_ready()


def is_semantic_embedding_active() -> bool:
    return _engine.is_semantic_embedding_active()


def semantic_search(query: str, top_k: int = 6, category_filter: Optional[str] = None, only_current: bool = False):
    return _engine.semantic_search(query, top_k=top_k, category_filter=category_filter, only_current=only_current)


def expand_related(db, results, max_depth: int = 1):
    return _engine.expand_related(db, results, max_depth=max_depth)


def __getattr__(name):
    # PEP 562 module-level attribute proxy: `matching_engine._indexed_standards`
    # is read directly (not through a function call) by main.py's /api/health
    # endpoint and by tests/conftest.py, so it has to keep working as a bare
    # attribute — but the actual list now lives on the engine singleton and
    # is reassigned on every rebuild_index(). A plain module-level list
    # copied once at import time would go stale after the first rebuild; this
    # proxy always reflects the engine's current state instead.
    if name == "_indexed_standards":
        return _engine.indexed_standards
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
