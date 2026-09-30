"""
Computes recommendation-quality metrics against EVAL_DATASET, using whatever
standards are currently indexed (live database, not a frozen snapshot — if an
admin edits the catalogue, re-running this reflects that immediately).

Metrics implemented, with the single-relevant-document-per-query simplification
stated explicitly (each eval query has exactly one correct expected standard,
which is the realistic shape of this problem — a procurement query has one
"right" primary standard, with allied/normative standards being a separate,
already-tested expansion mechanism, not part of this ranking metric):

- Hit@K       : fraction of queries where the expected standard appears
                anywhere in the top-K results. Equivalent to Recall@K when
                there is exactly one relevant document per query.
- Precision@K : Hit@K / K — the fraction of the K returned slots that were
                "correct", under the same single-relevant-doc simplification.
- MRR         : Mean Reciprocal Rank — 1/rank of the expected standard,
                averaged across queries (0 if not found in top-K).
- NDCG@K      : 1/log2(rank+1) averaged across queries (0 if not found) —
                the standard single-relevant-document form of NDCG.
- F1@K        : harmonic mean of Precision@K and Hit@K (=Recall@K here).

This runs entirely in-process against the live TF-IDF/embedding index — no
external services, so it's free-tier safe to expose as an on-demand endpoint.
"""
import math
from typing import List

from . import matching_engine
from .eval_dataset import EVAL_DATASET


def evaluate(top_k: int = 5) -> dict:
    per_query = []
    hits = 0
    reciprocal_ranks = []
    ndcg_values = []

    for case in EVAL_DATASET:
        results, _norm, _script, _embed = matching_engine.semantic_search(case["query"], top_k=top_k)
        is_numbers = [r[0].is_number for r in results]

        rank = None
        if case["expected_is_number"] in is_numbers:
            rank = is_numbers.index(case["expected_is_number"]) + 1

        hit = rank is not None
        rr = (1.0 / rank) if hit else 0.0
        ndcg = (1.0 / math.log2(rank + 1)) if hit else 0.0

        hits += 1 if hit else 0
        reciprocal_ranks.append(rr)
        ndcg_values.append(ndcg)

        per_query.append({
            "query": case["query"],
            "expected_is_number": case["expected_is_number"],
            "rank_of_expected": rank,
            "hit_at_k": hit,
            "reciprocal_rank": round(rr, 4),
            "top_result_is_number": is_numbers[0] if is_numbers else None,
        })

    n = len(EVAL_DATASET) or 1
    hit_at_k = hits / n
    precision_at_k = hit_at_k / top_k
    mrr = sum(reciprocal_ranks) / n
    ndcg_at_k = sum(ndcg_values) / n
    f1_at_k = (2 * precision_at_k * hit_at_k / (precision_at_k + hit_at_k)) if (precision_at_k + hit_at_k) > 0 else 0.0

    return {
        "top_k": top_k,
        "total_queries": len(EVAL_DATASET),
        "hit_at_k": round(hit_at_k, 4),
        "precision_at_k": round(precision_at_k, 4),
        "mrr": round(mrr, 4),
        "ndcg_at_k": round(ndcg_at_k, 4),
        "f1_at_k": round(f1_at_k, 4),
        "per_query": per_query,
    }


if __name__ == "__main__":
    # Standalone CLI run: `python -m app.evaluation` against a live-seeded DB.
    from .database import SessionLocal

    db = SessionLocal()
    try:
        matching_engine.rebuild_index(db)
    finally:
        db.close()

    metrics = evaluate(top_k=5)
    print(f"Evaluated {metrics['total_queries']} queries at top_k={metrics['top_k']}:")
    print(f"  Hit@K:       {metrics['hit_at_k']:.2%}")
    print(f"  Precision@K: {metrics['precision_at_k']:.2%}")
    print(f"  MRR:         {metrics['mrr']:.4f}")
    print(f"  NDCG@K:      {metrics['ndcg_at_k']:.4f}")
    print(f"  F1@K:        {metrics['f1_at_k']:.4f}")
    print()
    for pq in metrics["per_query"]:
        status = f"rank {pq['rank_of_expected']}" if pq["hit_at_k"] else "MISS"
        print(f"  [{status:>8}] {pq['query'][:60]:<60} -> expected {pq['expected_is_number']}")
