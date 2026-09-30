"""
Detects IS-standard-number-shaped tokens inside free text. Used for two
purposes:
  1. `expand_related()`'s graph traversal (unchanged behaviour, moved here
     from matching_engine.py verbatim).
  2. NEW — exact identifier search: if a procurement officer's query itself
     contains something that looks like an IS number ("IS 456", "IS 4031
     (Part 1):1988"), the matching standard should be a guaranteed top hit
     regardless of its lexical/semantic score, because that's an exact,
     unambiguous request — not a candidate for "the model thinks this is
     similar."
"""
import re
from typing import List, Optional

IS_NUMBER_RE = re.compile(r"IS[\s/]?\d{2,6}(?:\s*\([^)]*\))?(?::\d{4})?")

# A looser pattern for *query* scanning: officers often type "456" or
# "IS456" or "is 456:2000" with inconsistent spacing/case. This is
# deliberately broader than IS_NUMBER_RE (which is used against clean
# catalogue reference strings) since a query is messier free text.
_QUERY_IDENTIFIER_RE = re.compile(r"\bIS[\s/-]?(\d{2,6})(?:\s*\([^)]*\))?(?::\s?(\d{4}))?")


def extract_is_numbers(text: str) -> List[str]:
    """Used by graph traversal over normative_references free-text entries."""
    return IS_NUMBER_RE.findall(text)


def extract_query_identifier(query: str) -> Optional[str]:
    """Returns the bare numeric part (e.g. "456") of the first IS-number-
    shaped token found in a *query* string, or None. Deliberately returns
    just the digits, not a formatted "IS 456:2000" string, because the
    caller matches it as a prefix against the catalogue's own is_number
    field — the query's year/part suffix (if any) may not match the
    catalogue's exactly (a user typing "IS 456" should still find
    "IS 456:2000").
    """
    m = _QUERY_IDENTIFIER_RE.search(query)
    if not m:
        return None
    return m.group(1)


def matches_identifier(is_number: str, query_identifier: str) -> bool:
    """True if a catalogue standard's is_number contains the bare numeric
    identifier extracted from a query, as a real number token (not a
    substring of a different number — "45" must not match "IS 456")."""
    return bool(re.search(rf"\b0*{re.escape(query_identifier)}\b", is_number))
