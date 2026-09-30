import { useEffect, useState } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingState from "../../components/LoadingState";
import StandardForm from "../../components/StandardForm";
import Badge from "../../components/Badge";
import { Plus, Pencil, Trash2 } from "lucide-react";

export default function ManageStandards() {
  const [standards, setStandards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingNumber, setEditingNumber] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/api/standards", { params: { status: "" } }).then((res) => setStandards(res.data)).finally(() => setLoading(false));
  }
  useEffect(load, []);

  const filtered = standards.filter(
    (s) => !search || s.title.toLowerCase().includes(search.toLowerCase()) || s.is_number.toLowerCase().includes(search.toLowerCase())
  );

  async function handleCreate(payload) {
    setSubmitting(true);
    setError("");
    try {
      await client.post("/api/standards", payload);
      setCreating(false);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not create standard.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(isNumber, payload) {
    setSubmitting(true);
    setError("");
    try {
      await client.put(`/api/standards/${encodeURIComponent(isNumber)}`, payload);
      setEditingNumber(null);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not save changes.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(isNumber) {
    if (!confirm(`Delete ${isNumber}? This removes it from the live index immediately.`)) return;
    await client.delete(`/api/standards/${encodeURIComponent(isNumber)}`);
    load();
  }

  async function handleVerify(isNumber) {
    setSubmitting(true);
    setError("");
    try {
      await client.put(`/api/standards/${encodeURIComponent(isNumber)}/verify`, {});
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not mark as verified.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell>
      <div className="flex items-start justify-between flex-wrap gap-3 mb-6">
        <div>
          <div className="font-mono text-[12px] text-seal-700 mb-1">STANDARDS CUSTODIAN</div>
          <h1 className="font-display text-3xl font-medium mb-1">Manage Standards</h1>
          <p className="text-black/55 text-[14.5px]">
            Every create, edit, or delete instantly rebuilds the live semantic search index — nothing here is static.
          </p>
        </div>
        {!creating && (
          <button onClick={() => { setCreating(true); setEditingNumber(null); }}
            className="flex items-center gap-1.5 bg-indigo-800 hover:bg-indigo-900 text-white px-4 py-2.5 rounded-sm text-[13.5px] font-medium">
            <Plus size={15} /> New Standard
          </button>
        )}
      </div>

      {error && <div className="text-seal-700 text-[13px] bg-seal-100 border border-seal-600/25 rounded-sm px-3 py-2 mb-4">{error}</div>}

      {creating && (
        <StandardForm onSubmit={handleCreate} onCancel={() => setCreating(false)} submitting={submitting} />
      )}

      <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter by title or IS number…"
        className="w-full border border-line rounded-sm px-3.5 py-2.5 text-[13.5px] bg-white focus:outline-none focus:ring-2 focus:ring-indigo-800/40 mb-4" />

      {loading ? (
        <LoadingState />
      ) : (
        <div className="space-y-2">
          {filtered.map((s) => (
            <div key={s.is_number}>
              {editingNumber === s.is_number ? (
                <StandardForm initial={s} onSubmit={(payload) => handleUpdate(s.is_number, payload)}
                  onCancel={() => setEditingNumber(null)} submitting={submitting} />
              ) : (
                <div className="bg-white border border-line rounded-sm px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[12.5px] text-indigo-800">{s.is_number}</span>
                      <Badge tone={s.status === "PUBLISHED" ? "green" : s.status === "WITHDRAWN" ? "seal" : "gold"}>{s.status}</Badge>
                      <Badge tone={s.last_verified_at ? "green" : "gold"}>
                        {s.last_verified_at ? `verified ${new Date(s.last_verified_at).toLocaleDateString()}` : "unverified"}
                      </Badge>
                    </div>
                    <div className="text-[14px] font-medium">{s.title}</div>
                    <div className="text-[11.5px] text-black/40 font-mono">{s.category}</div>
                  </div>
                  <div className="flex items-center gap-3 text-[12.5px]">
                    {!s.last_verified_at && (
                      <button onClick={() => handleVerify(s.is_number)} disabled={submitting}
                        className="flex items-center gap-1 text-emerald-700 hover:underline disabled:opacity-50">Mark verified</button>
                    )}
                    <button onClick={() => { setEditingNumber(s.is_number); setCreating(false); }}
                      className="flex items-center gap-1 text-indigo-800 hover:underline"><Pencil size={13} /> Edit</button>
                    <button onClick={() => handleDelete(s.is_number)}
                      className="flex items-center gap-1 text-seal-700 hover:underline"><Trash2 size={13} /> Delete</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
