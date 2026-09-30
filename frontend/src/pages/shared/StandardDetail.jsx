import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import Badge from "../../components/Badge";
import { useAuth } from "../../context/AuthContext";
import { ArrowLeft, FlagTriangleRight, ShieldCheck, ShieldAlert } from "lucide-react";
import LoadingState from "../../components/LoadingState";

export default function StandardDetail() {
  const { isNumber } = useParams();
  const { user } = useAuth();
  const [std, setStd] = useState(null);
  const [allied, setAllied] = useState([]);
  const [loading, setLoading] = useState(true);
  const [flagOpen, setFlagOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [flagMsg, setFlagMsg] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verifySource, setVerifySource] = useState("");
  const [verifyOpen, setVerifyOpen] = useState(false);

  function load() {
    setLoading(true);
    return client.get(`/api/standards/${encodeURIComponent(isNumber)}`).then(async (res) => {
      setStd(res.data);
      const numbers = res.data.allied_standards || [];
      const fetched = await Promise.all(
        numbers.map((n) => client.get(`/api/standards/${encodeURIComponent(n)}`).then((r) => r.data).catch(() => null))
      );
      setAllied(fetched.filter(Boolean));
    }).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, [isNumber]);

  async function submitFlag() {
    if (!reason.trim()) return;
    await client.post("/api/change-requests", { standard_is_number: isNumber, reason: reason.trim() });
    setFlagMsg("Flagged for review. The Standards Custodian has been notified.");
    setFlagOpen(false);
    setReason("");
  }

  async function submitVerify() {
    setVerifying(true);
    try {
      await client.put(`/api/standards/${encodeURIComponent(isNumber)}/verify`, {
        source_reference: verifySource.trim() || null,
      });
      setVerifyOpen(false);
      setVerifySource("");
      await load();
    } finally {
      setVerifying(false);
    }
  }

  if (loading) return <AppShell><LoadingState /></AppShell>;
  if (!std) return <AppShell><div className="font-mono text-[13px] text-seal-700">Standard not found.</div></AppShell>;

  return (
    <AppShell>
      <Link to="/standards" className="inline-flex items-center gap-1.5 text-[13px] text-indigo-800 mb-5 hover:underline">
        <ArrowLeft size={14} /> Back to catalogue
      </Link>

      <div className="bg-white border border-line border-l-4 border-l-indigo-800 rounded-sm p-7 mb-8">
        <div className="flex items-start justify-between flex-wrap gap-3 mb-2">
          <div className="font-mono text-[15px] font-medium text-indigo-800">{std.is_number}</div>
          <Badge tone="neutral">{std.status}</Badge>
        </div>
        <h1 className="font-display text-2xl font-medium mb-3">{std.title}</h1>
        <p className="text-black/65 text-[14.5px] leading-relaxed mb-5">{std.scope}</p>

        <div className="grid sm:grid-cols-2 gap-5 text-[13px] mb-5">
          <Field label="Category" value={std.category} />
          <Field label="Latest Version" value={std.latest_version || "—"} />
          <Field label="Amendments">
            {std.amendments?.length ? std.amendments.map((a, i) => <Badge key={i} tone="seal">{a}</Badge>) : <Empty />}
          </Field>
          <Field label="Certification Requirement">
            {std.certification?.length ? std.certification.map((c, i) => <Badge key={i} tone="gold">{c}</Badge>) : <Empty />}
          </Field>
          <Field label="Normative References">
            {std.normative_references?.length ? std.normative_references.map((n, i) => <Badge key={i}>{n}</Badge>) : <Empty />}
          </Field>
          <Field label="Keywords">
            {std.keywords?.length ? std.keywords.map((k, i) => <Badge key={i} tone="neutral">{k}</Badge>) : <Empty />}
          </Field>
        </div>

        <div className={`flex items-start gap-2.5 rounded-sm px-4 py-3 mb-5 text-[12.5px] ${
          std.last_verified_at ? "bg-emerald-50 border border-emerald-600/25" : "bg-gold-100 border border-gold-600/30"
        }`}>
          {std.last_verified_at ? (
            <ShieldCheck size={16} className="text-emerald-700 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert size={16} className="text-gold-700 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            {std.last_verified_at ? (
              <div>
                <span className="font-medium">Verified {new Date(std.last_verified_at).toLocaleDateString()}</span>
                {std.source_reference && <span className="text-black/55"> · Source: {std.source_reference}</span>}
              </div>
            ) : (
              <div className="text-black/70">
                <span className="font-medium">Not yet verified by a Standards Custodian.</span>{" "}
                Cross-check this record against bis.gov.in before citing it in a live tender.
              </div>
            )}
            {user?.role === "ADMIN" && (
              verifyOpen ? (
                <div className="flex flex-wrap gap-2 mt-2">
                  <input value={verifySource} onChange={(e) => setVerifySource(e.target.value)}
                    placeholder="Source checked (e.g. BIS catalogue page / gazette notification)"
                    className="flex-1 min-w-[240px] border border-line rounded-sm px-3 py-1.5 text-[12.5px] bg-white focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
                  <button onClick={submitVerify} disabled={verifying}
                    className="bg-indigo-800 hover:bg-indigo-900 disabled:opacity-60 text-white text-[12px] px-3 py-1.5 rounded-sm">
                    {verifying ? "Saving…" : "Confirm verified"}
                  </button>
                  <button onClick={() => setVerifyOpen(false)} className="text-black/50 text-[12px] px-2">Cancel</button>
                </div>
              ) : (
                <button onClick={() => setVerifyOpen(true)} className="text-indigo-800 text-[12.5px] hover:underline mt-1.5 inline-block">
                  Mark as verified
                </button>
              )
            )}
          </div>
        </div>

        {user?.role !== "ADMIN" && (
          <div className="pt-4 border-t border-line">
            {flagMsg ? (
              <div className="text-emerald-700 text-[13px]">{flagMsg}</div>
            ) : flagOpen ? (
              <div className="flex flex-wrap gap-2">
                <input value={reason} onChange={(e) => setReason(e.target.value)}
                  placeholder="Reason — e.g. this version appears superseded…"
                  className="flex-1 min-w-[220px] border border-line rounded-sm px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
                <button onClick={submitFlag} className="bg-seal-600 hover:bg-seal-700 text-white text-[12.5px] px-3.5 py-2 rounded-sm">Submit</button>
                <button onClick={() => setFlagOpen(false)} className="text-black/50 text-[12.5px] px-2">Cancel</button>
              </div>
            ) : (
              <button onClick={() => setFlagOpen(true)} className="flex items-center gap-1.5 text-[13px] text-seal-700 hover:underline">
                <FlagTriangleRight size={14} /> Flag this standard as outdated or incorrect
              </button>
            )}
          </div>
        )}
      </div>

      {allied.length > 0 && (
        <>
          <h2 className="font-mono text-[12px] uppercase tracking-wide text-gold-700 border-b border-line pb-2 mb-4">
            Allied · Normative · Cross-Referenced Standards
          </h2>
          <div className="space-y-3">
            {allied.map((a) => (
              <Link key={a.is_number} to={`/standards/${encodeURIComponent(a.is_number)}`}
                className="block bg-white border border-line border-l-4 border-l-gold-600 rounded-sm p-4 hover:border-indigo-800/30 transition-colors">
                <div className="font-mono text-[13px] text-gold-700 mb-1">{a.is_number}</div>
                <div className="font-medium text-[14.5px]">{a.title}</div>
              </Link>
            ))}
          </div>
        </>
      )}
    </AppShell>
  );
}

function Field({ label, value, children }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-wide text-black/40 mb-1.5">{label}</div>
      {value ? <div>{value}</div> : <div className="flex flex-wrap gap-1">{children}</div>}
    </div>
  );
}
function Empty() {
  return <span className="text-black/35 text-[12.5px]">None specified</span>;
}
