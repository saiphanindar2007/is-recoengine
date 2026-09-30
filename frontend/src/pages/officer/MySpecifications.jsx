import { useEffect, useState } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingState from "../../components/LoadingState";
import { Trash2, CheckCircle2, FileEdit, X } from "lucide-react";

export default function MySpecifications() {
  const [specs, setSpecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // spec being edited (notes)
  const [notesDraft, setNotesDraft] = useState("");

  function load() {
    setLoading(true);
    client.get("/api/specifications").then((res) => setSpecs(res.data)).finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function removeNumber(spec, isNumber) {
    const updated = spec.standard_numbers.filter((n) => n !== isNumber);
    await client.put(`/api/specifications/${spec.id}`, { standard_numbers: updated });
    load();
  }

  async function finalize(spec) {
    await client.put(`/api/specifications/${spec.id}`, { status: spec.status === "FINALIZED" ? "DRAFT" : "FINALIZED" });
    load();
  }

  async function remove(spec) {
    if (!confirm(`Delete specification "${spec.title}"? This cannot be undone.`)) return;
    await client.delete(`/api/specifications/${spec.id}`);
    load();
  }

  function openNotes(spec) {
    setEditing(spec.id);
    setNotesDraft(spec.notes || "");
  }

  async function saveNotes(spec) {
    await client.put(`/api/specifications/${spec.id}`, { notes: notesDraft });
    setEditing(null);
    load();
  }

  return (
    <AppShell>
      <div className="mb-6">
        <div className="font-mono text-[12px] text-seal-700 mb-1">PROCUREMENT WORKSPACE</div>
        <h1 className="font-display text-3xl font-medium mb-2">My Specifications</h1>
        <p className="text-black/55 text-[14.5px]">
          Tender specification packages you've built from recommended standards. Finalize once ready to attach to a tender.
        </p>
      </div>

      {loading ? (
        <LoadingState />
      ) : specs.length === 0 ? (
        <div className="font-mono text-[13px] text-black/45 border border-dashed border-line rounded-sm p-8 text-center">
          No specifications yet. Go to <span className="text-indigo-800">Recommend Standards</span>, select results, and save them here.
        </div>
      ) : (
        <div className="space-y-4">
          {specs.map((spec) => (
            <div key={spec.id} className="bg-white border border-line rounded-sm p-5">
              <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                <div>
                  <div className="font-display text-lg font-medium">{spec.title}</div>
                  {spec.source_query && (
                    <div className="text-[12.5px] text-black/45 italic">from: "{spec.source_query}"</div>
                  )}
                </div>
                <span className={`font-mono text-[10.5px] px-2 py-1 rounded-sm border shrink-0 ${
                  spec.status === "FINALIZED" ? "bg-emerald-50 text-emerald-700 border-emerald-600/25" : "bg-gold-100 text-gold-700 border-gold-600/25"
                }`}>
                  {spec.status}
                </span>
              </div>

              <div className="flex flex-wrap gap-1.5 mb-3">
                {spec.standard_numbers.length === 0 ? (
                  <span className="text-black/35 text-[12.5px] font-mono">No standards added yet</span>
                ) : (
                  spec.standard_numbers.map((n) => (
                    <span key={n} className="inline-flex items-center gap-1 font-mono text-[11px] bg-indigo-100 text-indigo-900 border border-indigo-800/15 rounded-sm px-2 py-1">
                      {n}
                      <button onClick={() => removeNumber(spec, n)} className="hover:text-seal-700"><X size={11} /></button>
                    </span>
                  ))
                )}
              </div>

              {editing === spec.id ? (
                <div className="mb-3">
                  <textarea value={notesDraft} onChange={(e) => setNotesDraft(e.target.value)} rows={2}
                    placeholder="Internal notes for this specification…"
                    className="w-full border border-line rounded-sm px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40 mb-2" />
                  <div className="flex gap-2">
                    <button onClick={() => saveNotes(spec)} className="bg-indigo-800 text-white text-[12px] px-3 py-1.5 rounded-sm">Save notes</button>
                    <button onClick={() => setEditing(null)} className="text-black/50 text-[12px] px-2">Cancel</button>
                  </div>
                </div>
              ) : spec.notes ? (
                <p className="text-[13px] text-black/60 mb-3 bg-paper rounded-sm px-3 py-2">{spec.notes}</p>
              ) : null}

              <div className="flex items-center gap-3 text-[12px] pt-3 border-t border-line">
                <button onClick={() => finalize(spec)} className="flex items-center gap-1.5 text-emerald-700 hover:underline">
                  <CheckCircle2 size={14} /> {spec.status === "FINALIZED" ? "Revert to draft" : "Mark finalized"}
                </button>
                {editing !== spec.id && (
                  <button onClick={() => openNotes(spec)} className="flex items-center gap-1.5 text-indigo-800 hover:underline">
                    <FileEdit size={14} /> {spec.notes ? "Edit notes" : "Add notes"}
                  </button>
                )}
                <button onClick={() => remove(spec)} className="flex items-center gap-1.5 text-seal-700 hover:underline ml-auto">
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
