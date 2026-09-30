import Badge from "./Badge";
import { Link } from "react-router-dom";

export default function StandardCard({ standard, allied = false, action, selected, onToggleSelect }) {
  const relationLabel = standard.relations?.includes("normative") && standard.relations?.includes("allied")
    ? "allied + normative reference"
    : standard.relations?.includes("normative")
    ? "normative reference"
    : allied ? "allied reference" : null;

  return (
    <div
      className={`relative bg-white border rounded-sm p-5 mb-3 transition-colors ${
        allied ? "border-l-4 border-l-gold-600 border-line" : "border-l-4 border-l-indigo-800 border-line"
      } ${selected ? "ring-2 ring-indigo-800/40" : ""} ${standard.is_current === false ? "opacity-90" : ""}`}
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to={`/standards/${encodeURIComponent(standard.is_number)}`}
            className="font-mono text-[13.5px] font-medium text-indigo-800 hover:underline"
          >
            {standard.is_number}
          </Link>
          {standard.is_current === false && (
            <Badge tone="seal">superseded{standard.superseded_by ? ` by ${standard.superseded_by}` : ""}</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {typeof standard.relevance_score === "number" && standard.relevance_score !== null && (
            <span className="font-mono text-[11px] text-black/45">
              relevance {(standard.relevance_score * 100).toFixed(1)}%
            </span>
          )}
          {standard.confidence && (
            <Badge tone={standard.confidence === "HIGH" ? "green" : standard.confidence === "MEDIUM" ? "gold" : "seal"}>
              {standard.confidence} confidence
            </Badge>
          )}
          {relationLabel && <Badge tone="gold">{relationLabel}</Badge>}
          {onToggleSelect && (
            <button
              onClick={() => onToggleSelect(standard.is_number)}
              className={`font-mono text-[11px] px-2 py-1 rounded-sm border transition-colors ${
                selected
                  ? "bg-indigo-800 text-white border-indigo-800"
                  : "bg-white text-indigo-800 border-indigo-800/30 hover:border-indigo-800"
              }`}
            >
              {selected ? "✓ added" : "+ add to spec"}
            </button>
          )}
        </div>
      </div>

      <div className="font-semibold text-[16px] mt-1.5 mb-1.5 leading-snug">{standard.title}</div>
      <p className="text-[13.5px] text-black/60 mb-2 leading-relaxed">{standard.scope}</p>

      {standard.matched_terms?.length > 0 && (
        <div className="mb-2 text-[12px] text-black/50">
          <span className="font-mono text-[10px] uppercase tracking-wide text-black/35 mr-1.5">Why matched:</span>
          {standard.matched_terms.map((t, i) => (
            <span key={i} className="inline-block bg-indigo-100/70 text-indigo-900 rounded-sm px-1.5 py-0.5 mr-1 mb-1">
              {t}
            </span>
          ))}
        </div>
      )}

      {standard.evidence_snippet && (
        <div className="mb-3 text-[12px] text-black/55 italic border-l-2 border-indigo-800/20 pl-2.5">
          "{standard.evidence_snippet}"
        </div>
      )}

      {standard.score_breakdown && (
        <div className="mb-3 font-mono text-[10.5px] text-black/40 flex gap-3">
          <span>lexical (TF-IDF): {(standard.score_breakdown.tfidf * 100).toFixed(1)}%</span>
          {standard.score_breakdown.embedding !== null && standard.score_breakdown.embedding !== undefined && (
            <span>semantic (embedding): {(standard.score_breakdown.embedding * 100).toFixed(1)}%</span>
          )}
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-3 text-[12.5px]">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-black/40 mb-1">Latest Version</div>
          <div>{standard.latest_version || "—"}</div>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-black/40 mb-1">Amendments</div>
          <div className="flex flex-wrap gap-1">
            {standard.amendments?.length ? (
              standard.amendments.map((a, i) => <Badge key={i} tone="seal">{a}</Badge>)
            ) : (
              <span className="text-black/35">None recorded</span>
            )}
          </div>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-black/40 mb-1">Certification</div>
          <div className="flex flex-wrap gap-1">
            {standard.certification?.length ? (
              standard.certification.map((c, i) => <Badge key={i} tone="gold">{c}</Badge>)
            ) : (
              <span className="text-black/35">None specified</span>
            )}
          </div>
        </div>
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wide text-black/40 mb-1">Normative References</div>
          <div className="flex flex-wrap gap-1">
            {standard.normative_references?.length ? (
              standard.normative_references.map((n, i) => <Badge key={i}>{n}</Badge>)
            ) : (
              <span className="text-black/35">None specified</span>
            )}
          </div>
        </div>
      </div>

      {action}
    </div>
  );
}
