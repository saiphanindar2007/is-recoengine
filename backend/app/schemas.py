import datetime as dt
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, EmailStr, Field, field_validator

# ---------------- Auth ----------------

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "OFFICER"
    department: Optional[str] = None
    designation: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    department: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool
    created_at: dt.datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut


# ---------------- Standards ----------------

class StandardBase(BaseModel):
    is_number: str
    title: str
    category: str
    scope: str
    latest_version: Optional[str] = ""
    amendments: List[str] = []
    allied_standards: List[str] = []
    normative_references: List[str] = []
    certification: List[str] = []
    keywords: List[str] = []
    status: str = "PUBLISHED"
    is_current: bool = True
    superseded_by: Optional[str] = None
    source_reference: Optional[str] = None


class StandardCreate(StandardBase):
    pass


class StandardUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    scope: Optional[str] = None
    latest_version: Optional[str] = None
    amendments: Optional[List[str]] = None
    allied_standards: Optional[List[str]] = None
    normative_references: Optional[List[str]] = None
    certification: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    status: Optional[str] = None
    is_current: Optional[bool] = None
    superseded_by: Optional[str] = None
    source_reference: Optional[str] = None


class StandardVerify(BaseModel):
    """Payload for PUT /api/standards/{is_number}/verify — an explicit,
    auditable human-verification action, not something that happens as a
    side effect of any other write."""
    source_reference: Optional[str] = None
    note: Optional[str] = None


class StandardOut(StandardBase):
    id: int
    created_at: dt.datetime
    updated_at: dt.datetime
    last_verified_at: Optional[dt.datetime] = None
    verified_by_id: Optional[int] = None
    relevance_score: Optional[float] = None
    confidence: Optional[str] = None   # HIGH | MEDIUM | LOW - derived from relevance_score, see matching_engine
    matched_terms: List[str] = []
    evidence_snippet: Optional[str] = None  # verbatim excerpt from title/scope containing the matched terms
    relations: List[str] = []   # populated only for allied/normative expansion entries
    # Was Dict[str, Optional[float]] — widened because the multi-feature
    # reranker (app/search/ranking.py) adds boolean flags like
    # "exact_identifier_match" alongside numeric adjustments such as
    # "currency_adjustment", and both need to serialize as their real type,
    # not be silently coerced to a float.
    score_breakdown: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ---------------- Recommend ----------------

class RecommendRequest(BaseModel):
    query: str
    top_k: int = 6
    category_filter: Optional[str] = None
    only_current: bool = False


class RecommendResponse(BaseModel):
    query: str
    normalized_query: str
    detected_script: str
    embeddings_used: bool
    match_status: str            # MATCHED | LOW_CONFIDENCE | NO_MATCH
    guidance: Optional[str] = None
    results: List[StandardOut]
    allied_expansion: List[StandardOut]
    total_candidates_scanned: int


class ClauseMatch(BaseModel):
    clause_index: int
    clause_preview: str
    matches: List[StandardOut]


class DocumentRecommendResponse(RecommendResponse):
    extracted_text_preview: str
    source_filename: str
    clauses_processed: int
    clause_matches: List[ClauseMatch] = []


# ---------------- Saved specs ----------------

class SavedSpecCreate(BaseModel):
    title: str
    source_query: Optional[str] = None
    standard_numbers: List[str] = []
    notes: Optional[str] = None
    status: str = "DRAFT"


class SavedSpecUpdate(BaseModel):
    title: Optional[str] = None
    standard_numbers: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class SavedSpecOut(BaseModel):
    id: int
    owner_id: int
    title: str
    source_query: Optional[str]
    standard_numbers: List[str]
    notes: Optional[str]
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


# ---------------- Change requests ----------------

class ChangeRequestCreate(BaseModel):
    standard_is_number: str
    reason: str


class ChangeRequestResolve(BaseModel):
    status: str  # IN_REVIEW | RESOLVED | REJECTED
    resolution_note: Optional[str] = None


class ChangeRequestOut(BaseModel):
    id: int
    standard_is_number: str
    raised_by_id: int
    reason: str
    status: str
    resolution_note: Optional[str]
    resolved_by_id: Optional[int]
    created_at: dt.datetime
    resolved_at: Optional[dt.datetime]

    class Config:
        from_attributes = True


# ---------------- Analytics ----------------

class AnalyticsSummary(BaseModel):
    total_standards: int
    total_users: int
    total_queries: int
    total_saved_specs: int
    open_change_requests: int
    queries_last_7_days: int
    embeddings_active: bool
    top_categories: List[dict]
    top_matched_standards: List[dict]
    recent_queries: List[dict]
    outdated_standards_count: int


# ---------------- Audit log ----------------

class AuditLogOut(BaseModel):
    id: int
    actor_email: Optional[str]
    actor_role: Optional[str]
    action: str
    target_type: str
    target_id: Optional[str]
    detail: Dict[str, Any]
    created_at: dt.datetime

    class Config:
        from_attributes = True


# ---------------- Recommendation quality evaluation ----------------

class EvalQueryResult(BaseModel):
    query: str
    expected_is_number: str
    rank_of_expected: Optional[int]   # 1-based rank if found within top_k, else None
    hit_at_k: bool
    reciprocal_rank: float
    top_result_is_number: Optional[str]


class EvaluationSummary(BaseModel):
    top_k: int
    total_queries: int
    hit_at_k: float          # equivalent to Recall@K with exactly one relevant doc per query
    precision_at_k: float    # hit_at_k / top_k, since only one relevant doc exists per query
    mrr: float                # Mean Reciprocal Rank
    ndcg_at_k: float
    f1_at_k: float
    per_query: List[EvalQueryResult]
