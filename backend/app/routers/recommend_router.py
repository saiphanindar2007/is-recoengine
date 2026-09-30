import io
import re
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas, auth, matching_engine
from ..database import get_db
from ..rate_limit import limiter

logger = logging.getLogger("is_reco.recommend")
router = APIRouter(prefix="/api/recommend", tags=["recommend"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024   # 5 MB
EXTRACTION_TIMEOUT_SECONDS = 15
# Single source of truth for the "low confidence" cutoff — matching_engine's
# per-result confidence label and this response-level guidance must never
# drift apart, so both read the same constant.
LOW_CONFIDENCE_THRESHOLD = matching_engine.CONFIDENCE_MEDIUM_THRESHOLD
MAX_CLAUSES_PROCESSED = 8            # bounds compute on a free-tier CPU

_extraction_pool = ThreadPoolExecutor(max_workers=2)


def _to_out(std: models.Standard, score=None, terms=None, relations=None, breakdown=None) -> schemas.StandardOut:
    out = schemas.StandardOut.model_validate(std)
    out.relevance_score = round(score, 4) if score is not None else None
    out.matched_terms = terms or []
    out.relations = relations or []
    out.score_breakdown = breakdown
    if score is not None:
        out.confidence = matching_engine.confidence_tier(score)
        out.evidence_snippet = matching_engine.evidence_snippet_for(std, terms or [])
    return out


def _match_status_and_guidance(results):
    if not results:
        return "NO_MATCH", (
            "No standard matched with sufficient confidence. Try adding more technical "
            "detail: material, application, rated capacity/voltage/pressure, and intended "
            "end-use, or select a narrower category filter."
        )
    top_score = results[0][1]
    if top_score < LOW_CONFIDENCE_THRESHOLD:
        return "LOW_CONFIDENCE", (
            "The best match had low confidence — verify it against the scope text before "
            "relying on it, and consider adding more specific technical detail to the query."
        )
    return "MATCHED", None


def _run_search(db: Session, query: str, top_k: int, category_filter, only_current: bool):
    results, norm_query, detected_script, embeddings_used = matching_engine.semantic_search(
        query, top_k=top_k, category_filter=category_filter, only_current=only_current
    )
    related = matching_engine.expand_related(db, results)
    match_status, guidance = _match_status_and_guidance(results)
    return results, related, norm_query, detected_script, embeddings_used, match_status, guidance


def _log_query(db: Session, user: models.User, query: str, norm_query: str, detected_script: str,
                embeddings_used: bool, results, category_filter, source: str):
    log = models.QueryLog(
        user_id=user.id,
        query_text=query,
        normalized_query=norm_query,
        detected_script=detected_script,
        embeddings_used=embeddings_used,
        top_match_is_number=results[0][0].is_number if results else None,
        top_match_score=results[0][1] if results else None,
        result_count=len(results),
        category_filter=category_filter,
        source=source,
    )
    db.add(log)
    db.commit()


@router.post("", response_model=schemas.RecommendResponse)
@limiter.limit("30/minute")
def recommend(
    request: Request,
    payload: schemas.RecommendRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query text must not be empty.")

    results, related, norm_query, detected_script, embeddings_used, match_status, guidance = _run_search(
        db, payload.query, payload.top_k, payload.category_filter, payload.only_current
    )
    _log_query(db, current_user, payload.query, norm_query, detected_script, embeddings_used,
               results, payload.category_filter, source="TEXT")

    total = len(matching_engine._indexed_standards) if matching_engine.is_index_ready() else 0
    return schemas.RecommendResponse(
        query=payload.query,
        normalized_query=norm_query,
        detected_script=detected_script,
        embeddings_used=embeddings_used,
        match_status=match_status,
        guidance=guidance,
        results=[_to_out(s, sc, terms, breakdown=bd) for s, sc, terms, bd in results],
        allied_expansion=[_to_out(r["standard"], relations=r["relations"]) for r in related],
        total_candidates_scanned=total,
    )


# --------------------------------------------------------------------------- #
# Document upload: validation, safe text extraction, clause-level processing
# --------------------------------------------------------------------------- #

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

# Splits on numbered clause headers ("1.", "1.1", "Clause 5", "Section 3.2") or
# blank-line-delimited paragraphs — a pragmatic heuristic for tender documents,
# not a full document-structure parser.
_CLAUSE_SPLIT_RE = re.compile(
    r"(?:\n\s*(?:\d{1,2}(?:\.\d{1,2})*\.?\s+|Clause\s+\d+[:.]?\s*|Section\s+\d+(?:\.\d+)?[:.]?\s*))",
    re.IGNORECASE,
)


def _validate_upload(file: UploadFile, raw: bytes) -> str:
    name = (file.filename or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload a .pdf, .docx, or .txt file.")

    # Basic magic-byte sniffing so a renamed file can't slip past the extension check.
    if ext == ".pdf" and not raw.startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="File has a .pdf extension but is not a valid PDF.")
    if ext == ".docx" and not raw.startswith(b"PK"):  # .docx is a zip archive
        raise HTTPException(status_code=422, detail="File has a .docx extension but is not a valid Word document.")
    return ext


def _extract_text(ext: str, raw: bytes) -> str:
    if ext == ".pdf":
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages[:20]:  # cap pages for free-tier CPU/time budget
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    if ext == ".docx":
        import docx
        document = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in document.paragraphs)
    return raw.decode("utf-8", errors="ignore")


def _extract_text_with_timeout(ext: str, raw: bytes) -> str:
    future = _extraction_pool.submit(_extract_text, ext, raw)
    try:
        return future.result(timeout=EXTRACTION_TIMEOUT_SECONDS)
    except FutureTimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Text extraction took longer than {EXTRACTION_TIMEOUT_SECONDS}s and was aborted. "
                   "Try a smaller or simpler document.",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Document extraction failed: {exc}")
        raise HTTPException(status_code=422, detail="Could not extract text from this document. It may be corrupted or scanned/image-only.")


def _split_into_clauses(text: str) -> list:
    raw_clauses = _CLAUSE_SPLIT_RE.split(text)
    clauses = [c.strip() for c in raw_clauses if c and len(c.strip()) >= 40]
    if not clauses:
        # fall back to paragraph splitting if the numbered-clause heuristic found nothing
        clauses = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= 40]
    if not clauses and text.strip():
        clauses = [text.strip()]
    # Process the longest (most information-dense) clauses first, bounded for CPU/time.
    clauses.sort(key=len, reverse=True)
    return clauses[:MAX_CLAUSES_PROCESSED]


@router.post("/upload", response_model=schemas.DocumentRecommendResponse)
@limiter.limit("10/minute")
def recommend_from_document(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
    file: UploadFile = File(...),
    top_k: int = 6,
):
    """Accepts a tender document (.pdf/.docx/.txt), validates it (extension +
    magic bytes), extracts text under a hard timeout, splits it into clauses,
    and runs EACH clause through the recommendation pipeline separately —
    rather than truncating the whole document to one blind excerpt. Results
    are aggregated (deduplicated, highest score kept) into a single ranked
    list, with the full per-clause breakdown also returned for transparency
    about which part of the tender drove which recommendation."""
    raw = file.file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 5MB.")
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    ext = _validate_upload(file, raw)
    text = _extract_text_with_timeout(ext, raw)
    if not text or not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from this document.")

    clauses = _split_into_clauses(text)

    # Aggregate best-scoring result per standard across all processed clauses.
    aggregate: dict = {}
    clause_matches_out = []
    embeddings_used_any = False
    detected_script = "latin"

    for idx, clause in enumerate(clauses):
        results, _rel, norm_q, script, embed_used, _status, _guidance = _run_search(
            db, clause, min(top_k, 4), None, False
        )
        embeddings_used_any = embeddings_used_any or embed_used
        if script != "latin":
            detected_script = script

        clause_out = []
        for std, score, terms, breakdown in results:
            clause_out.append(_to_out(std, score, terms, breakdown=breakdown))
            existing = aggregate.get(std.is_number)
            if not existing or score > existing[1]:
                aggregate[std.is_number] = (std, score, terms, breakdown)

        clause_matches_out.append(schemas.ClauseMatch(
            clause_index=idx,
            clause_preview=clause[:200],
            matches=clause_out,
        ))

    ranked = sorted(aggregate.values(), key=lambda r: -r[1])[:top_k]
    related = matching_engine.expand_related(db, ranked) if ranked else []
    match_status, guidance = _match_status_and_guidance(ranked)

    _log_query(db, current_user, text[:500], text[:500], detected_script, embeddings_used_any,
               ranked, None, source="DOCUMENT_UPLOAD")

    total = len(matching_engine._indexed_standards) if matching_engine.is_index_ready() else 0

    return schemas.DocumentRecommendResponse(
        query=f"[Uploaded document: {file.filename}]",
        normalized_query=text[:200],
        detected_script=detected_script,
        embeddings_used=embeddings_used_any,
        match_status=match_status,
        guidance=guidance,
        results=[_to_out(s, sc, terms, breakdown=bd) for s, sc, terms, bd in ranked],
        allied_expansion=[_to_out(r["standard"], relations=r["relations"]) for r in related],
        total_candidates_scanned=total,
        extracted_text_preview=text.strip()[:800],
        source_filename=file.filename or "uploaded_document",
        clauses_processed=len(clauses),
        clause_matches=clause_matches_out,
    )
