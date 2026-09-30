import { useEffect, useState } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingState from "../../components/LoadingState";
import Badge from "../../components/Badge";
import { Link } from "react-router-dom";

export default function ChangeRequests() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(null);
  const [note, setNote] = useState("");

  function load() {
    setLoading(true);
    client.get("/api/change-requests").then((res) => setItems(res.data)).finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function resolve(id, status) {
    await client.put(`/api/change-requests/${id}/resolve`, { status, resolution_note: note || null });
    setResolving(null);
    setNote("");
    load();
  }

  return (
    <AppShell>
      <div className="mb-6">
        <div className="font-mono text-[12px] text-seal-700 mb-1">STANDARDS CUSTODIAN</div>
        <h1 className="font-display text-3xl font-medium mb-1">Change Requests</h1>
        <p className="text-black/55 text-[14.5px]">Standards flagged by procurement officers as outdated, incorrect, or ambiguous.</p>
      </div>

      {loading ? (
        <LoadingState />
      ) : items.length === 0 ? (
        <div className="font-mono text-[13px] text-black/45 border border-dashed border-line rounded-sm p-8 text-center">
          No change requests have been raised.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((cr) => (
            <div key={cr.id} className="bg-white border border-line rounded-sm p-5">
              <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                <Link to={`/standards/${encodeURIComponent(cr.standard_is_number)}`} className="font-mono text-[13px] text-indigo-800 hover:underline">
                  {cr.standard_is_number}
                </Link>
                <Badge tone={cr.status === "OPEN" ? "seal" : cr.status === "RESOLVED" ? "green" : cr.status === "REJECTED" ? "neutral" : "gold"}>
                  {cr.status}
                </Badge>
              </div>
              <p className="text-[13.5px] text-black/70 mb-3">{cr.reason}</p>
              <div className="text-[11.5px] text-black/40 font-mono mb-3">
                Raised {new Date(cr.created_at).toLocaleString()}
              </div>

              {cr.resolution_note && (
                <div className="text-[12.5px] bg-paper rounded-sm px-3 py-2 mb-3">
                  <span className="font-mono text-[10px] uppercase text-black/40">Resolution note</span><br />
                  {cr.resolution_note}
                </div>
              )}

              {(cr.status === "OPEN" || cr.status === "IN_REVIEW") && (
                resolving === cr.id ? (
                  <div className="flex flex-wrap gap-2">
                    <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Resolution note…"
                      className="flex-1 min-w-[200px] border border-line rounded-sm px-3 py-1.5 text-[12.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
                    <button onClick={() => resolve(cr.id, "RESOLVED")} className="bg-emerald-600 hover:bg-emerald-700 text-white text-[12px] px-3 py-1.5 rounded-sm">Resolve</button>
                    <button onClick={() => resolve(cr.id, "REJECTED")} className="bg-seal-600 hover:bg-seal-700 text-white text-[12px] px-3 py-1.5 rounded-sm">Reject</button>
                    <button onClick={() => setResolving(null)} className="text-black/50 text-[12px] px-2">Cancel</button>
                  </div>
                ) : (
                  <div className="flex gap-3 text-[12.5px]">
                    {cr.status === "OPEN" && (
                      <button onClick={() => resolve(cr.id, "IN_REVIEW")} className="text-gold-700 hover:underline">Mark in review</button>
                    )}
                    <button onClick={() => setResolving(cr.id)} className="text-indigo-800 hover:underline">Resolve / Reject</button>
                  </div>
                )
              )}
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
