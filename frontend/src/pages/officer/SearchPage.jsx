import { useEffect, useState, useRef } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import StandardCard from "../../components/StandardCard";
import { Search as SearchIcon, Loader2, FolderPlus, Upload, FileText, X } from "lucide-react";

const EXAMPLES = [
  "PVC pipes for potable water supply, underground housing scheme",
  "Household mixer grinder — safety compliance for retail sale",
  "TMT reinforcement bars for a multi-storey RCC building",
  "Solar photovoltaic modules for a rooftop installation tender",
  "Portland cement for a bridge construction project",
  "Lithium-ion battery pack for electric two-wheeler",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [onlyCurrent, setOnlyCurrent] = useState(false);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [saveOpen, setSaveOpen] = useState(false);
  const [specTitle, setSpecTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [uploadedFile, setUploadedFile] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    client.get("/api/standards/categories").then((res) => setCategories(res.data.categories));
  }, []);

  async function runSearch(q) {
    const text = (q ?? query).trim();
    if (!text) return;
    setQuery(text);
    setLoading(true);
    setError("");
    setSaveMsg("");
    setUploadedFile(null);
    try {
      const res = await client.post("/api/recommend", {
        query: text, top_k: 6, category_filter: category || null, only_current: onlyCurrent,
      });
      setResult(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not run the recommendation. Try again.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError("");
    setSaveMsg("");
    setQuery("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await client.post("/api/recommend/upload?top_k=6", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
      setUploadedFile(file.name);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not process this document.");
      setResult(null);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function toggleSelect(isNumber) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(isNumber) ? next.delete(isNumber) : next.add(isNumber);
      return next;
    });
  }

  async function saveSpecification() {
    if (!specTitle.trim() || selected.size === 0) return;
    setSaving(true);
    try {
      await client.post("/api/specifications", {
        title: specTitle.trim(),
        source_query: query || `Document: ${uploadedFile}`,
        standard_numbers: Array.from(selected),
        status: "DRAFT",
      });
      setSaveMsg(`Saved "${specTitle.trim()}" with ${selected.size} standard(s) to your workspace.`);
      setSaveOpen(false);
      setSpecTitle("");
      setSelected(new Set());
    } catch {
      setSaveMsg("Could not save the specification. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <div className="mb-6">
        <div className="font-mono text-[12px] text-seal-700 mb-1">SEMANTIC RECOMMENDATION</div>
        <h1 className="font-display text-3xl font-medium mb-2">Recommend Applicable Standards</h1>
        <p className="text-black/55 text-[14.5px] max-w-2xl">
          Describe what you're procuring, or upload a tender document (.pdf/.docx/.txt). Matching
          combines lexical relevance with dense semantic similarity when available.
        </p>
      </div>

      <div className="bg-white border border-line rounded-sm p-5 mb-2">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. Supply of uPVC pipes for potable water distribution in a housing scheme, DN 110mm, underground laying..."
          rows={3}
          className="w-full border border-line rounded-sm px-3.5 py-3 text-[15px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40 resize-none mb-3"
        />
        <div className="flex flex-wrap items-center gap-2">
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="font-mono text-[12.5px] border border-line rounded-sm px-3 py-2 bg-white">
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <label className="flex items-center gap-1.5 font-mono text-[12px] text-black/60 cursor-pointer select-none">
            <input type="checkbox" checked={onlyCurrent} onChange={(e) => setOnlyCurrent(e.target.checked)} />
            current standards only
          </label>

          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={handleFileUpload} />
          <button onClick={() => fileInputRef.current?.click()} disabled={loading}
            className="flex items-center gap-1.5 border border-line hover:border-indigo-800/40 text-black/60 hover:text-indigo-800 px-3 py-2 rounded-sm text-[12.5px] transition-colors">
            <Upload size={14} /> Upload tender document
          </button>

          <button onClick={() => runSearch()} disabled={loading}
            className="ml-auto flex items-center gap-2 bg-indigo-800 hover:bg-indigo-900 disabled:opacity-60 text-white px-5 py-2 rounded-sm text-[13.5px] font-medium transition-colors">
            {loading ? <Loader2 size={15} className="animate-spin" /> : <SearchIcon size={15} />}
            {loading ? "Matching…" : "Recommend Standards"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => runSearch(ex)}
              className="font-mono text-[11px] px-2.5 py-1 border border-line rounded-sm text-black/50 hover:border-indigo-800/40 hover:text-indigo-800 transition-colors">
              {ex}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="text-seal-700 text-[13.5px] bg-seal-100 border border-seal-600/25 rounded-sm px-4 py-2.5 mb-4">{error}</div>}
      {saveMsg && <div className="text-emerald-700 text-[13.5px] bg-emerald-50 border border-emerald-600/25 rounded-sm px-4 py-2.5 mb-4">{saveMsg}</div>}

      {result && result.match_status !== "MATCHED" && (
        <div className={`text-[13.5px] rounded-sm px-4 py-2.5 mb-4 border ${
          result.match_status === "NO_MATCH"
            ? "text-seal-700 bg-seal-100 border-seal-600/25"
            : "text-gold-700 bg-gold-100 border-gold-600/25"
        }`}>
          <span className="font-mono text-[10.5px] uppercase tracking-wide mr-2">
            {result.match_status === "NO_MATCH" ? "No confident match" : "Low confidence"}
          </span>
          {result.guidance}
        </div>
      )}

      {uploadedFile && result && (
        <div className="flex items-start gap-2 bg-indigo-100/50 border border-indigo-800/15 rounded-sm px-4 py-3 mb-4 text-[12.5px]">
          <FileText size={15} className="text-indigo-800 mt-0.5 shrink-0" />
          <div>
            <div className="font-medium mb-1">Extracted from {uploadedFile}</div>
            <div className="text-black/55 italic">"{result.extracted_text_preview}..."</div>
          </div>
          <button onClick={() => { setUploadedFile(null); setResult(null); }} className="ml-auto text-black/40 hover:text-seal-700"><X size={14} /></button>
        </div>
      )}

      {result && (
        <>
          <div className="flex items-center justify-between flex-wrap gap-3 mt-6 mb-3">
            <div className="font-mono text-[11.5px] text-black/45 flex items-center gap-2 flex-wrap">
              <span>Matched against {result.total_candidates_scanned} indexed standards</span>
              <span className={`px-1.5 py-0.5 rounded-sm border ${result.embeddings_used ? "border-emerald-600/30 text-emerald-700 bg-emerald-50" : "border-line text-black/40"}`}>
                {result.embeddings_used ? "hybrid semantic (TF-IDF + embeddings)" : "TF-IDF matching"}
              </span>
              {result.detected_script !== "latin" && (
                <span className="px-1.5 py-0.5 rounded-sm border border-gold-600/30 text-gold-700 bg-gold-100">
                  {result.detected_script} script detected &amp; normalized
                </span>
              )}
            </div>
            {selected.size > 0 && (
              <button onClick={() => setSaveOpen(true)}
                className="flex items-center gap-1.5 bg-gold-600 hover:bg-gold-700 text-white px-3.5 py-1.5 rounded-sm text-[12.5px] font-medium transition-colors">
                <FolderPlus size={14} /> Save {selected.size} selected to specification
              </button>
            )}
          </div>

          {saveOpen && (
            <div className="bg-white border border-gold-600/40 rounded-sm p-4 mb-4 flex flex-wrap items-center gap-2">
              <input value={specTitle} onChange={(e) => setSpecTitle(e.target.value)}
                placeholder="Specification title, e.g. Housing Scheme Phase-2 Plumbing Tender"
                className="flex-1 min-w-[240px] border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
              <button onClick={saveSpecification} disabled={saving || !specTitle.trim()}
                className="bg-indigo-800 hover:bg-indigo-900 disabled:opacity-50 text-white px-4 py-2 rounded-sm text-[13px] font-medium">
                {saving ? "Saving…" : "Save"}
              </button>
              <button onClick={() => setSaveOpen(false)} className="text-black/50 text-[13px] px-2">Cancel</button>
            </div>
          )}

          <h2 className="font-mono text-[12px] uppercase tracking-wide text-indigo-800 border-b border-line pb-2 mb-3">
            Recommended Standards
          </h2>
          {result.results.length === 0 ? (
            <div className="font-mono text-[13px] text-black/45 border border-dashed border-line rounded-sm p-6 text-center">
              No confidently matching standard found. Try adding more technical detail (material,
              application, voltage/pressure rating, end-use).
            </div>
          ) : (
            result.results.map((s) => (
              <StandardCard key={s.is_number} standard={s} selected={selected.has(s.is_number)} onToggleSelect={toggleSelect} />
            ))
          )}

          {result.allied_expansion.length > 0 && (
            <>
              <h2 className="font-mono text-[12px] uppercase tracking-wide text-gold-700 border-b border-line pb-2 mb-3 mt-8">
                Allied · Normative · Cross-Referenced Standards
              </h2>
              {result.allied_expansion.map((s) => (
                <StandardCard key={s.is_number} standard={s} allied selected={selected.has(s.is_number)} onToggleSelect={toggleSelect} />
              ))}
            </>
          )}
        </>
      )}
    </AppShell>
  );
}
