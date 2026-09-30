"""
Precomputed vector index for dense-embedding similarity search.

The embedding matrix is computed ONCE per `rebuild_index()` call (not per
query) and cached here, L2-normalized, so every query only pays for encoding
the query itself plus a single matrix-vector product — this is the
"precomputed vector index" the retrieval layer needs, as opposed to
re-encoding the whole corpus on every request.

Search is exact brute-force cosine similarity (a normalized dot product),
not an approximate-nearest-neighbour index (FAISS/Annoy/hnswlib). This is a
deliberate choice, not a gap: at this corpus's realistic scale (dozens to a
few thousand Indian Standards), brute-force is both exact and faster in
wall-clock terms than the overhead an ANN index adds, and it keeps the
hybrid blend (`(1-w)*lexical + w*semantic`, computed elementwise across the
FULL corpus) mathematically simple — an ANN index would only return a
top-k subset, breaking that elementwise blend. If the corpus ever grows to
a scale where brute-force stops being viable (tens of thousands of
standards+), this class's `.search_scores()` signature is the intended
drop-in replacement point for a FAISS `IndexFlatIP` — the caller
(`search/engine.py`) never needs to change.
"""
from typing import Optional

import numpy as np


class VectorIndex:
    def __init__(self):
        self._matrix: Optional[np.ndarray] = None

    def build(self, embed_matrix) -> None:
        """`embed_matrix` is expected already L2-normalized (the embedder is
        called with `normalize_embeddings=True`), so cosine similarity
        reduces to a plain dot product — precomputing that normalization
        once here, at build time, is what makes per-query search cheap."""
        self._matrix = np.asarray(embed_matrix) if embed_matrix is not None else None

    @property
    def is_built(self) -> bool:
        return self._matrix is not None

    def search_scores(self, query_vec) -> np.ndarray:
        """query_vec: a single already-normalized embedding vector (shape
        (1, dim) or (dim,)). Returns a 1D cosine-similarity array, one score
        per indexed document, in original corpus order."""
        q = np.asarray(query_vec).reshape(1, -1)
        return (q @ self._matrix.T).flatten()
