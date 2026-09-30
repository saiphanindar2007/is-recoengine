"""
Domain-aware text preprocessing for procurement queries.

Three layers, applied in order:

  1. Script normalization (`_TERM_MAP`) — transliterates common Hindi/Tamil/
     Telugu procurement terms into English so the (English-vocabulary) index
     can match non-Latin-script queries. Unchanged from the original engine.

  2. Domain synonym expansion (`DOMAIN_SYNONYMS`) — British/American spelling
     variants and common Indian-procurement abbreviations (PVC, GI, MS, HDPE,
     RCC...) are expanded ADDITIVELY: the original token is kept AND the
     expansion is appended, so an exact abbreviation match in a document
     still hits, while a query using the long form also hits a document that
     only wrote the abbreviation (or vice versa).

  3. Lemmatization (`lemmatize`) — a small, dependency-free, rule-based
     lemmatizer (plurals, -ing/-ed verb forms, -ly adverbs). Deliberately NOT
     nltk's WordNetLemmatizer or spaCy: both need a downloaded corpus/model,
     which is a network dependency on first cold start — exactly the kind of
     free-tier fragility this project has consistently avoided elsewhere
     (see matching_engine's embedding fallback). A rule-based lemmatizer is
     zero-network, zero-extra-dependency, and "good enough" for matching
     query inflections ("pipes"/"piping"/"piped") to a document's base form
     ("pipe") — which is the actual practical goal here, not linguistic
     perfection.

     Domain-aware: any token that looks like an identifier, code, or acronym
     (contains a digit, is all-uppercase, or is 2 letters or fewer) is left
     untouched — "IS", "PVC", "456:2000" must never be stemmed.
"""
import re
from typing import Tuple

# ---------------------------------------------------------------------------
# Layer 1 — multilingual transliteration (unchanged from the original engine)
# ---------------------------------------------------------------------------
_TERM_MAP = {
    "सीमेंट": "cement", "सीमेण्ट": "cement", "स्टील": "steel", "लोहा": "iron steel",
    "पानी": "water", "पाइप": "pipe", "बिजली": "electrical", "तार": "wire cable",
    "खिलौना": "toy", "सुरक्षा": "safety", "पंखा": "fan", "मोटर": "motor",
    "सोना": "gold", "पानी की टंकी": "water tank", "नल": "tap valve", "छत": "roof",
    "ईंट": "brick", "रेत": "sand", "बजरी": "aggregate gravel", "प्रमाणन": "certification",
    "मानक": "standard", "गुणवत्ता": "quality", "विद्युत": "electrical power",
    "जल": "water", "फ्रिज": "refrigerator", "वॉशिंग मशीन": "washing machine",
    "बैटरी": "battery", "सोलर पैनल": "solar panel", "पंप": "pump",
    "சிமெண்ட்": "cement", "எஃகு": "steel", "தண்ணீர்": "water", "பாதுகாப்பு": "safety",
    "సిమెంట్": "cement", "ఉక్కు": "steel", "నీరు": "water", "భద్రత": "safety",
}

# ---------------------------------------------------------------------------
# Layer 2 — domain synonyms: spelling variants + procurement abbreviations
# common in Indian Standards catalogue text. Additive: `key -> expansion`
# means the query gets BOTH `key` and `expansion`'s words, never a
# replacement, so nothing that already worked can start failing.
# ---------------------------------------------------------------------------
DOMAIN_SYNONYMS = {
    # British/American spelling — IS titles are British-spelled, technicians
    # and officers often type American spellings interchangeably.
    "color": "colour", "aluminum": "aluminium", "fiber": "fibre",
    "liter": "litre", "liters": "litres", "meter": "metre", "meters": "metres",
    "sulfate": "sulphate", "vapor": "vapour", "tire": "tyre",
    # Common Indian-procurement material/product abbreviations, expanded to
    # their full form so a query using either form matches a document using
    # the other.
    "pvc": "polyvinyl chloride", "upvc": "unplasticized polyvinyl chloride",
    "gi": "galvanized iron galvanised iron", "cgi": "corrugated galvanized iron",
    "ms": "mild steel", "ss": "stainless steel",
    "hdpe": "high density polyethylene", "ldpe": "low density polyethylene",
    "rcc": "reinforced cement concrete", "pcc": "plain cement concrete",
    "frp": "fibre reinforced plastic", "mcb": "miniature circuit breaker",
    "elcb": "earth leakage circuit breaker", "isi": "indian standards institute mark",
    "bis": "bureau of indian standards", "crs": "compulsory registration scheme",
    "geyser": "water heater", "torch": "flashlight",
}

_IDENTIFIER_TOKEN_RE = re.compile(r"^\d|^[A-Z]{2,}$|^[A-Za-z]{1,2}$")
_WORD_RE = re.compile(r"[A-Za-z]+")


def _looks_like_identifier(token: str) -> bool:
    """True for tokens that must never be stemmed: contain a digit, are
    short acronyms (<=2 letters), or are ALL-CAPS codes."""
    return bool(re.search(r"\d", token)) or (len(token) <= 2) or token.isupper()


# Domain nouns that happen to end in "-ing" but are NOT verb progressive
# forms in this domain's usage — "cladding", "flooring", "piping" (as a
# material/system, not the verb), etc. are as fundamental a noun here as
# "pipe" or "valve". Checked before the generic verb-suffix stripping so
# these aren't reduced to a meaningless/wrong verb stem ("cladding" -> "clad").
_PROTECTED_DOMAIN_NOUNS = {
    "cladding", "flooring", "glazing", "plumbing", "shuttering",
    "waterproofing", "flashing", "moulding", "molding", "panelling",
    "paneling", "tooling",
}

# Procurement/technical specification text is noun-heavy: "fittings",
# "bearings", "housings", "coatings", "castings" — plural OR singular — are
# almost always nouns naming a component or material, essentially never a
# verb progressive tense ("the technician is fitting the valve" barely
# occurs in catalogue/spec text). So the DEFAULT for any bare "-ing" word
# not already handled above is to leave it unchanged (matches the "-ings"
# plural rule's noun-preserving behaviour, and keeps "fitting"/"fittings"
# both reducing to the same "fitting" form — the actual thing that matters
# for retrieval, more than picking the textbook-correct dictionary lemma).
# Only words on this explicit allowlist get the verb-stem reduction below —
# common genuine verb gerunds worth normalizing to their root.
_VERB_GERUND_ALLOWLIST = {
    "testing", "certifying", "welding", "threading", "using", "running",
    "piping", "writing", "sampling", "hopping", "stopping", "supplying",
    "installing", "manufacturing", "grouting", "packing", "labelling",
    "labeling", "marking", "storing", "handling",
}


# Adverb -> adjective reduction ("thermally" -> "thermal") is done via an
# explicit lookup, NOT a blind "-ly" suffix rule. A suffix rule is too risky
# here: many core domain/procurement nouns and verbs happen to end in "ly"
# without being adjective+ly adverbs at all — "supply", "apply", "comply",
# "reply", "multiply", "assembly" all end in "ly" and were getting mangled
# ("supply" -> "supp", "assembly" -> "assemb") by an earlier suffix-based
# version of this rule. "supply" in particular is about as core a term as
# this application has. A curated lookup of genuinely useful technical
# adverb reductions has zero false-positive risk; it just doesn't reduce
# every possible adverb, which is a fine trade for never breaking "supply".
_ADVERB_LOOKUP = {
    "thermally": "thermal", "electrically": "electrical", "mechanically": "mechanical",
    "chemically": "chemical", "annually": "annual", "manually": "manual",
    "vertically": "vertical", "horizontally": "horizontal", "structurally": "structural",
    "internally": "internal", "externally": "external", "generally": "general",
    "automatically": "automatic", "optically": "optical", "electronically": "electronic",
    "hydraulically": "hydraulic", "pneumatically": "pneumatic", "visually": "visual",
    "periodically": "periodic", "physically": "physical",
}


def _lemmatize_token(token: str) -> str:
    if _looks_like_identifier(token) or len(token) <= 3:
        return token
    low = token.lower()
    if low in _PROTECTED_DOMAIN_NOUNS:
        return low
    if low in _ADVERB_LOOKUP:
        return _ADVERB_LOOKUP[low]

    # Gerund-derived NOUNS, pluralized ("fittings", "bearings", "housings",
    # "coatings", "buildings") — extremely common in industrial/procurement
    # text. "-ing" verb forms never take a plural "s" in English, so any
    # word ending in "ings" is unambiguously this noun pattern, never a
    # verb — it must reduce to the singular noun ("fitting"), NOT get its
    # "-ing" stripped as if it were a verb progressive ("fit"). This has to
    # be checked, and returned, before the generic verb-suffix handling
    # below, or "fittings" -> "fitting" -> (wrongly, as a verb) -> "fit".
    if low.endswith("ings") and len(low) > 5:
        return low[:-1]

    # Plurals
    if low.endswith("ies") and len(low) > 4:
        return low[:-3] + "y"
    if low.endswith(("xes", "ches", "shes", "sses")):
        return low[:-2]
    if low.endswith("oes") and len(low) > 4:
        return low[:-2]
    if low.endswith("s") and not low.endswith("ss") and len(low) > 3:
        low = low[:-1]

    # Verb inflections: -ing / -ied / -ed, with double-consonant undo
    # ("running" -> "runn" -> "run") and silent-e restoration
    # ("piping" -> "pip" -> "pipe", "using" -> "us" -> "use") — English
    # doubles a final consonant before "-ing"/"-ed" exactly when the root
    # has NO silent e (hop -> hopping), and does NOT double when the root
    # DOES end in a silent e that "-ing" simply replaces (pipe -> piping).
    # Distinguishing these is what makes "piping" reduce to "pipe" instead
    # of the wrong "pip". -ing is gated by the allowlist above (see comment
    # there); anything not on it is left as-is, matching the "-ings" plural
    # rule's noun-preserving default.
    if low.endswith("ing") and len(low) >= 5 and low in _VERB_GERUND_ALLOWLIST:
        return _restore_verb_stem(low[:-3])
    if low.endswith("ied") and len(low) > 5:
        return low[:-3] + "y"
    if low.endswith("ed") and len(low) >= 4 and not low.endswith("eed"):
        return _restore_verb_stem(low[:-2])

    return low


def _restore_verb_stem(stem: str) -> str:
    """runn -> run (doubled consonant, no silent e in the root); but
    pip -> pipe, us -> use, writ -> write (single closed syllable, root
    ends in a silent e that "-ing"/"-ed" replaced). Known limitation,
    same class as any rule-based stemmer: a root that is itself naturally
    double-consonant-ended (e.g. "process") can be mis-undoubled — accepted
    as a rare edge case rather than engineering a full syllable parser for
    marginal gain."""
    if len(stem) >= 4 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
        return stem[:-1]
    if len(stem) >= 2 and stem[-1] not in "aeiou" and stem[-2] in "aeiou" and (len(stem) == 2 or stem[-3] not in "aeiou"):
        return stem + "e"
    return stem


def lemmatize(text: str) -> str:
    """Lemmatizes every alphabetic word in `text`, leaving numbers,
    punctuation, and identifier-like tokens untouched."""
    def _sub(m):
        return _lemmatize_token(m.group(0))
    return _WORD_RE.sub(_sub, text)


def expand_domain_synonyms(text: str) -> str:
    """Additively appends the expansion for every recognized synonym/
    abbreviation token found in `text` (case-insensitive, whole-word)."""
    tokens = re.findall(r"[A-Za-z]+", text.lower())
    additions = []
    seen = set()
    for tok in tokens:
        if tok in DOMAIN_SYNONYMS and tok not in seen:
            additions.append(DOMAIN_SYNONYMS[tok])
            seen.add(tok)
    if not additions:
        return text
    return text + " " + " ".join(additions)


def normalize_query(text: str) -> Tuple[str, str]:
    """Full preprocessing pipeline for a raw user query:
    transliterate -> expand domain synonyms -> lemmatize.
    Returns (processed_query, detected_script) — signature unchanged from
    the original engine so callers/tests are unaffected.
    """
    detected = "latin"
    normalized = text
    for native, en in _TERM_MAP.items():
        if native in normalized:
            normalized = normalized.replace(native, f" {en} ")
            if re.search(r"[\u0900-\u097F]", native):
                detected = "devanagari"
            elif re.search(r"[\u0B80-\u0BFF]", native):
                detected = "tamil"
            elif re.search(r"[\u0C00-\u0C7F]", native):
                detected = "telugu"

    normalized = expand_domain_synonyms(normalized)
    normalized = lemmatize(normalized)
    return normalized, detected
