"""
Lexical retrieval, encapsulated as an index object rather than loose module
globals — the "clean modular architecture" the TF-IDF half of the hybrid
engine was missing. Behaviourally identical to the original engine's TF-IDF
step; this is a structural refactor, not a scoring change.
"""
from typing import List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class LexicalIndex:
    """A built TF-IDF index over a fixed corpus. Call `.build(corpus)` once
    per `rebuild_index()`, then `.search_scores(query)` per request."""

    def __init__(self):
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix = None

    def build(self, corpus: List[str]) -> None:
        self._vectorizer = TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), stop_words="english", max_features=8000
        )
        self._matrix = self._vectorizer.fit_transform(corpus)

    @property
    def is_built(self) -> bool:
        return self._vectorizer is not None and self._matrix is not None

    def search_scores(self, query: str):
        """Returns a 1D array of cosine-similarity scores, one per corpus
        document, in original corpus order."""
        q_vec = self._vectorizer.transform([query])
        return cosine_similarity(q_vec, self._matrix).flatten()

    def explain_terms(self, query: str, doc_idx: int, top_n: int = 6) -> List[str]:
        """The query/document terms that actually drove doc_idx's TF-IDF
        score — unchanged logic from the original engine's `_explain_terms`."""
        try:
            feature_names = self._vectorizer.get_feature_names_out()
            q_vec = self._vectorizer.transform([query]).toarray()[0]
            doc_vec = self._matrix[doc_idx].toarray()[0]
            contributions = q_vec * doc_vec
            top_idx = contributions.argsort()[::-1][:top_n]
            return [feature_names[i] for i in top_idx if contributions[i] > 0]
        except Exception:  # noqa: BLE001
            return []
