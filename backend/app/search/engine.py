"""
SearchEngine — the single orchestration point composing every retrieval
stage into the hybrid lexical + semantic + reranked pipeline:

    normalize/expand query
        -> lexical (TF-IDF) scores over the full corpus
        -> dense embedding scores over the full corpus (if enabled)
        -> blend
        -> multi-feature procurement rerank (exact identifier / currency /
           verification / certification-hint)
        -> threshold + category/currency filter + top_k cut

This replaces the old monolithic matching_engine.py's module-level globals
and functions with one class holding index state, composed from the smaller
single-responsibility modules in this package (preprocessing, lexical_index,
vector_index, embedder, ranking, graph). `matching_engine.py` is now a thin
backward-compatible facade over a module-level singleton of this class, so
every existing caller/import keeps working unchanged.
"""
import threading
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .. import models
from . import embedder, graph, preprocessing, ranking
from .lexical_index import LexicalIndex
from .vector_index import VectorIndex

HYBRID_WEIGHT_EMBED = 0.55
_SCORE_FLOOR = 0.02  # below this, a result is noise, not a recommendation


def _document_text(std: models.Standard) -> str:
    """Same field-weighting heuristic as the original engine (title
    weighted highest, then scope, then category/keywords), now also passed
    through the same lemmatizer applied to queries — matching preprocessing
    on both sides of the index is what makes lemmatization actually improve
    recall, rather than only normalizing one side of the comparison."""
    parts = [
        (std.title or "") * 3,
        (std.scope or "") * 2,
        std.category or "",
        " ".join(std.keywords or []) * 2,
    ]
    raw = " ".join(parts)
    return preprocessing.lemmatize(preprocessing.expand_domain_synonyms(raw))


class SearchEngine:
    def __init__(self):
        self._lock = threading.RLock()
        self._lexical = LexicalIndex()
        self._vector = VectorIndex()
        self.indexed_standards: List[models.Standard] = []
        self._embeddings_active = False

    # -- index lifecycle ----------------------------------------------
    def rebuild_index(self, db: Session) -> None:
        with self._lock:
            standards = (
                db.query(models.Standard)
                .filter(models.Standard.status == "PUBLISHED")
                .all()
            )
            if not standards:
                self._lexical = LexicalIndex()
                self._vector = VectorIndex()
                self.indexed_standards = []
                self._embeddings_active = False
                return

            corpus = [_document_text(s) for s in standards]
            self._lexical = LexicalIndex()
            self._lexical.build(corpus)

            self._vector = VectorIndex()
            self._embeddings_active = False
            model = embedder.try_load_embedder()
            if model is not None:
                try:
                    embed_matrix = model.encode(corpus, normalize_embeddings=True, show_progress_bar=False)
                    self._vector.build(embed_matrix)
                    self._embeddings_active = True
                except Exception:  # noqa: BLE001
                    self._vector = VectorIndex()

            self.indexed_standards = standards

    def is_index_ready(self) -> bool:
        return self._lexical.is_built and len(self.indexed_standards) > 0

    def is_semantic_embedding_active(self) -> bool:
        return self._embeddings_active and self._vector.is_built

    # -- retrieval ------------------------------------------------------
    def semantic_search(
        self, query: str, top_k: int = 6,
        category_filter: Optional[str] = None, only_current: bool = False,
    ):
        norm_query, detected_script = preprocessing.normalize_query(query)
        if not self.is_index_ready():
            return [], norm_query, detected_script, False

        with self._lock:
            lexical_scores = self._lexical.search_scores(norm_query)

            embeddings_used = False
            embed_scores = None
            if self.is_semantic_embedding_active():
                model = embedder.try_load_embedder()
                if model is not None:
                    try:
                        q_embed = model.encode([norm_query], normalize_embeddings=True, show_progress_bar=False)
                        embed_scores = self._vector.search_scores(q_embed)
                        blended = (1 - HYBRID_WEIGHT_EMBED) * lexical_scores + HYBRID_WEIGHT_EMBED * embed_scores
                        embeddings_used = True
                    except Exception:  # noqa: BLE001
                        blended = lexical_scores
                else:
                    blended = lexical_scores
            else:
                blended = lexical_scores

            # Build candidates over the FULL corpus, applying hard filters
            # (category / currency) before reranking, then rerank, then cut.
            candidates: List[Dict] = []
            for idx, std in enumerate(self.indexed_standards):
                if category_filter and std.category != category_filter:
                    continue
                if only_current and not std.is_current:
                    continue
                terms = self._lexical.explain_terms(norm_query, idx)
                breakdown = {
                    "tfidf": round(float(lexical_scores[idx]), 4),
                    "embedding": round(float(embed_scores[idx]), 4) if embed_scores is not None else None,
                }
                candidates.append({
                    "standard": std,
                    "base_score": float(blended[idx]),
                    "terms": terms,
                    "breakdown": breakdown,
                })

            candidates = ranking.rerank(candidates, raw_query=query)

            results = []
            for c in candidates:
                if c["final_score"] <= _SCORE_FLOOR:
                    continue
                results.append((c["standard"], c["final_score"], c["terms"], c["breakdown"]))
                if len(results) >= top_k:
                    break

        return results, norm_query, detected_script, embeddings_used

    def expand_related(self, db: Session, results, max_depth: int = 1):
        return graph.expand_related(db, results, max_depth=max_depth)


# Module-level singleton — one engine instance backs the whole process,
# matching the original module-globals engine's lifetime/scope exactly.
engine = SearchEngine()
