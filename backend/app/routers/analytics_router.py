import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas, auth, matching_engine
from ..database import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=schemas.AnalyticsSummary)
def summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN", "AUDITOR")),
):
    total_standards = db.query(models.Standard).count()
    total_users = db.query(models.User).count()
    total_queries = db.query(models.QueryLog).count()
    total_saved_specs = db.query(models.SavedSpecification).count()
    open_crs = db.query(models.StandardChangeRequest).filter(
        models.StandardChangeRequest.status.in_(["OPEN", "IN_REVIEW"])
    ).count()
    outdated_count = db.query(models.Standard).filter(models.Standard.is_current.is_(False)).count()

    since = dt.datetime.now(dt.UTC) - dt.timedelta(days=7)
    queries_last_7 = db.query(models.QueryLog).filter(models.QueryLog.created_at >= since).count()

    cat_rows = db.query(models.Standard.category, func.count(models.Standard.id)).group_by(
        models.Standard.category
    ).all()
    top_categories = [{"category": c, "count": n} for c, n in sorted(cat_rows, key=lambda r: -r[1])]

    match_rows = (
        db.query(models.QueryLog.top_match_is_number, func.count(models.QueryLog.id))
        .filter(models.QueryLog.top_match_is_number.isnot(None))
        .group_by(models.QueryLog.top_match_is_number)
        .all()
    )
    top_matched = [{"is_number": n, "count": c} for n, c in sorted(match_rows, key=lambda r: -r[1])[:10]]

    recent = (
        db.query(models.QueryLog)
        .order_by(models.QueryLog.created_at.desc())
        .limit(15)
        .all()
    )
    recent_out = [
        {
            "query_text": r.query_text,
            "top_match_is_number": r.top_match_is_number,
            "top_match_score": r.top_match_score,
            "source": r.source,
            "created_at": r.created_at.isoformat(),
        }
        for r in recent
    ]

    return schemas.AnalyticsSummary(
        total_standards=total_standards,
        total_users=total_users,
        total_queries=total_queries,
        total_saved_specs=total_saved_specs,
        open_change_requests=open_crs,
        queries_last_7_days=queries_last_7,
        embeddings_active=matching_engine.is_semantic_embedding_active(),
        top_categories=top_categories,
        top_matched_standards=top_matched,
        recent_queries=recent_out,
        outdated_standards_count=outdated_count,
    )


@router.get("/evaluation", response_model=schemas.EvaluationSummary)
def evaluation(
    top_k: int = 5,
    current_user: models.User = Depends(auth.require_roles("ADMIN", "AUDITOR")),
):
    """On-demand recommendation-quality evaluation against a labelled query set
    (app/eval_dataset.py), run live against whatever is currently indexed —
    not a cached/static report. See app/evaluation.py for metric definitions."""
    from .. import evaluation as eval_module
    return eval_module.evaluate(top_k=top_k)
