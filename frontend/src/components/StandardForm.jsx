import { useState } from "react";

const EMPTY = {
  is_number: "", title: "", category: "", scope: "", latest_version: "",
  amendments: "", allied_standards: "", normative_references: "", certification: "", keywords: "",
  status: "PUBLISHED", is_current: true, superseded_by: "", source_reference: "",
};

function toArr(s) { return s.split(",").map((x) => x.trim()).filter(Boolean); }
function toStr(a) { return (a || []).join(", "); }

export default function StandardForm({ initial, onSubmit, onCancel, submitting }) {
  const [form, setForm] = useState(
    initial
      ? {
          ...initial,
          amendments: toStr(initial.amendments),
          allied_standards: toStr(initial.allied_standards),
          normative_references: toStr(initial.normative_references),
          certification: toStr(initial.certification),
          keywords: toStr(initial.keywords),
        }
      : EMPTY
  );

  function update(field, value) { setForm((f) => ({ ...f, [field]: value })); }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit({
      ...form,
      amendments: toArr(form.amendments),
      allied_standards: toArr(form.allied_standards),
      normative_references: toArr(form.normative_references),
      certification: toArr(form.certification),
      keywords: toArr(form.keywords),
    });
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white border border-indigo-800/25 rounded-sm p-5 space-y-4 mb-5">
      <div className="grid sm:grid-cols-2 gap-4">
        <TextField label="IS Number" value={form.is_number} onChange={(v) => update("is_number", v)} required disabled={!!initial} mono />
        <TextField label="Category" value={form.category} onChange={(v) => update("category", v)} required />
      </div>
      <TextField label="Title" value={form.title} onChange={(v) => update("title", v)} required />
      <TextAreaField label="Scope" value={form.scope} onChange={(v) => update("scope", v)} required />
      <div className="grid sm:grid-cols-2 gap-4">
        <TextField label="Latest Version" value={form.latest_version} onChange={(v) => update("latest_version", v)} />
        <div>
          <FieldLabel>Status</FieldLabel>
          <select value={form.status} onChange={(e) => update("status", e.target.value)}
            className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] bg-white focus:outline-none focus:ring-2 focus:ring-indigo-800/40">
            <option value="PUBLISHED">PUBLISHED</option>
            <option value="DRAFT">DRAFT</option>
            <option value="UNDER_REVIEW">UNDER_REVIEW</option>
            <option value="WITHDRAWN">WITHDRAWN</option>
          </select>
        </div>
      </div>
      <TextField label="Amendments (comma separated)" value={form.amendments} onChange={(v) => update("amendments", v)} />
      <TextField label="Allied Standards — IS numbers (comma separated)" value={form.allied_standards} onChange={(v) => update("allied_standards", v)} mono />
      <TextField label="Normative References (comma separated)" value={form.normative_references} onChange={(v) => update("normative_references", v)} />
      <TextField label="Certification Requirements (comma separated)" value={form.certification} onChange={(v) => update("certification", v)} />
      <TextField label="Keywords (comma separated)" value={form.keywords} onChange={(v) => update("keywords", v)} />
      <TextField label="Source reference (where this data was checked, e.g. BIS catalogue URL / gazette notification)"
        value={form.source_reference || ""} onChange={(v) => update("source_reference", v)} />

      <div className="grid sm:grid-cols-2 gap-4 items-end">
        <label className="flex items-center gap-2 text-[13px] pb-2">
          <input type="checkbox" checked={form.is_current} onChange={(e) => update("is_current", e.target.checked)} />
          This is the current, in-force edition
        </label>
        {!form.is_current && (
          <TextField label="Superseded by (IS number)" value={form.superseded_by || ""} onChange={(v) => update("superseded_by", v)} mono />
        )}
      </div>

      <div className="flex gap-2 pt-2">
        <button type="submit" disabled={submitting}
          className="bg-indigo-800 hover:bg-indigo-900 disabled:opacity-60 text-white px-5 py-2 rounded-sm text-[13.5px] font-medium">
          {submitting ? "Saving…" : initial ? "Save changes" : "Create standard"}
        </button>
        <button type="button" onClick={onCancel} className="text-black/50 text-[13.5px] px-3">Cancel</button>
      </div>
    </form>
  );
}

function FieldLabel({ children }) {
  return <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">{children}</label>;
}
function TextField({ label, value, onChange, required, disabled, mono }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <input required={required} disabled={disabled} value={value} onChange={(e) => onChange(e.target.value)}
        className={`w-full border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40 disabled:bg-black/5 ${mono ? "font-mono" : ""}`} />
    </div>
  );
}
function TextAreaField({ label, value, onChange, required }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <textarea required={required} rows={3} value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40 resize-none" />
    </div>
  );
}
