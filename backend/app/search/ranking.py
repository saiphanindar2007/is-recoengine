"""
Procurement-specific multi-feature relevance/reranking engine.

The original engine used a single blended number (lexical + embedding) as
the final score. This module adds a second, explicit reranking stage on top
of that blend, using signals that are meaningful specifically for
*procurement* recommendations — not generic document relevance:

  - exact_identifier : the officer's query itself named an IS number — an
                        unambiguous request that should win over any amount
                        of semantic similarity from a different standard.
  - currency          : a superseded standard (is_current=False) is
                        deprioritized relative to an equally-relevant
                        current one — recommending an outdated standard in
                        a live tender is a real procurement risk.
  - verification       : a standard a custodian has actually verified
                        (last_verified_at is set) is nudged above an
                        otherwise-equal unverified one.
  - certification_hint : if the query itself mentions certification/
                        licensing language, standards that carry a
                        certification requirement are nudged up.

All adjustments are small relative to the base score EXCEPT the exact
identifier match, which is designed to dominate — see `EXACT_IDENTIFIER_FLOOR`.
Every adjustment is returned in the breakdown dict, not just folded silently
into one number, so explainability is preserved.
"""
from typing import Dict, List, Optional

from .. import models
from . import identifiers

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

CONFIDENCE_HIGH_THRESHOLD = 0.30
CONFIDENCE_MEDIUM_THRESHOLD = 0.12

EXACT_IDENTIFIER_FLOOR = 0.93   # an exact IS-number query match is guaranteed near the top
CURRENCY_PENALTY = 0.03
VERIFIED_BONUS = 0.015
CERTIFICATION_HINT_BONUS = 0.02

_CERTIFICATION_HINT_WORDS = ("certification", "certificate", "certified", "isi mark", "license", "licence", "bis mark")


def confidence_tier(score: float) -> str:
    if score >= CONFIDENCE_HIGH_THRESHOLD:
        return CONFIDENCE_HIGH
    if score >= CONFIDENCE_MEDIUM_THRESHOLD:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def evidence_snippet_for(std: models.Standard, matched_terms: List[str], window: int = 90) -> Optional[str]:
    """Finds the first matched term inside the standard's own scope (falling
    back to title), and returns a short verbatim excerpt around it — direct
    textual evidence the officer can check against the source document,
    rather than only an abstract term list."""
    if not matched_terms:
        return None
    haystacks = [std.scope or "", std.title or ""]
    for text in haystacks:
        lower = text.lower()
        for term in matched_terms:
            idx = lower.find(term.lower())
            if idx != -1:
                start = max(0, idx - window // 2)
                end = min(len(text), idx + len(term) + window // 2)
                snippet = text[start:end].strip()
                prefix = "…" if start > 0 else ""
                suffix = "…" if end < len(text) else ""
                return f"{prefix}{snippet}{suffix}"
    return None


def rerank(
    candidates: List[Dict],
    raw_query: str,
) -> List[Dict]:
    """`candidates` is a list of dicts, each with at least:
        {"standard": Standard, "base_score": float, "breakdown": {...}}
    Mutates and returns the same list with an adjusted "final_score" and an
    expanded "breakdown", re-sorted descending by final_score. Pure function
    otherwise — no I/O, no DB access, so it's trivially unit-testable.
    """
    query_lower = raw_query.lower()
    query_identifier = identifiers.extract_query_identifier(raw_query)
    wants_certification = any(w in query_lower for w in _CERTIFICATION_HINT_WORDS)

    for c in candidates:
        std = c["standard"]
        score = c["base_score"]
        adj = {}

        is_exact = bool(query_identifier and identifiers.matches_identifier(std.is_number, query_identifier))
        if is_exact:
            score = max(score, EXACT_IDENTIFIER_FLOOR)
            adj["exact_identifier_match"] = True

        if not std.is_current:
            score -= CURRENCY_PENALTY
            adj["currency_adjustment"] = -CURRENCY_PENALTY

        if getattr(std, "last_verified_at", None) is not None:
            score += VERIFIED_BONUS
            adj["verification_adjustment"] = VERIFIED_BONUS

        if wants_certification and (std.certification or []):
            score += CERTIFICATION_HINT_BONUS
            adj["certification_hint_adjustment"] = CERTIFICATION_HINT_BONUS

        score = max(0.0, min(1.0, score))
        c["final_score"] = score
        c["breakdown"] = {**c["breakdown"], **adj}

    candidates.sort(key=lambda c: -c["final_score"])
    return candidates
