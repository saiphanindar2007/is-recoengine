"""
Traverses BOTH allied_standards and normative_references edges out from a set
of primary results, deduplicated and tagged with which relation(s) produced
each entry. Logic unchanged from the original monolithic engine — moved here
as part of the modular split, not a behaviour change.
"""
import re
from typing import Dict, List

from .. import models
from .identifiers import extract_is_numbers


def expand_related(db, results, max_depth: int = 1):
    """Cycle-safe and depth-bounded by construction: `visited` accumulates
    every standard number already placed in the primary set or the
    expansion frontier, so a normative/allied reference cycle (A references
    B, B references A) cannot loop or duplicate work even if max_depth is
    increased in the future. Defaults to depth=1 (a single hop out from the
    primary matches), matching current product behaviour; the parameter
    exists so deeper traversal is a config change, not a rewrite.
    """
    primary_numbers = {s.is_number for s, _, _, _ in results}
    all_standards = db.query(models.Standard).all()
    by_number = {s.is_number: s for s in all_standards}

    def _resolve(no: str):
        std = by_number.get(no)
        if std:
            return std
        prefix = re.match(r"IS[\s/]?\d{2,6}", no)
        if prefix:
            for candidate_no, candidate in by_number.items():
                if candidate_no.startswith(prefix.group(0)):
                    return candidate
        return None

    def _edges_of(std) -> Dict[str, set]:
        edges: Dict[str, set] = {}
        for no in (std.allied_standards or []):
            edges.setdefault(no, set()).add("allied")
        for ref in (std.normative_references or []):
            for match in extract_is_numbers(ref):
                edges.setdefault(match.strip(), set()).add("normative")
        return edges

    visited = set(primary_numbers)
    relation_map: Dict[str, set] = {}
    frontier = [std for std, _, _, _ in results]

    for _depth in range(max_depth):
        next_frontier = []
        for std in frontier:
            for no, relations in _edges_of(std).items():
                if no in visited:
                    continue
                relation_map.setdefault(no, set()).update(relations)
                resolved = _resolve(no)
                if resolved and resolved.is_number not in visited:
                    next_frontier.append(resolved)
            visited.add(std.is_number)
        frontier = next_frontier
        if not frontier:
            break

    expanded = []
    for no, relations in relation_map.items():
        std = _resolve(no)
        if std:
            expanded.append({"standard": std, "relations": sorted(relations)})
    return expanded
