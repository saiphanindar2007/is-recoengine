import { useEffect, useState } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import StandardCard from "../../components/StandardCard";
import { useAuth } from "../../context/AuthContext";

export default function StandardsCatalogue() {
  const { user } = useAuth();
  const [standards, setStandards] = useState([]);
  const [categories, setCategories] = useState([]);
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    const params = {};
    if (category) params.category = category;
    if (search) params.search = search;
    client.get("/api/standards", { params }).then((res) => setStandards(res.data)).finally(() => setLoading(false));
  }

  useEffect(() => {
    client.get("/api/standards/categories").then((res) => setCategories(res.data.categories));
  }, []);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, search]);

  return (
    <AppShell>
      <div className="mb-6">
        <div className="font-mono text-[12px] text-seal-700 mb-1">CATALOGUE</div>
        <h1 className="font-display text-3xl font-medium mb-2">Standards Catalogue</h1>
        <p className="text-black/55 text-[14.5px]">Browse the full indexed corpus of Indian Standards.</p>
      </div>

      <div className="flex flex-wrap gap-2 mb-5">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by title or IS number…"
          className="flex-1 min-w-[220px] border border-line rounded-sm px-3.5 py-2.5 text-[13.5px] bg-white focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
        <select value={category} onChange={(e) => setCategory(e.target.value)}
          className="font-mono text-[12.5px] border border-line rounded-sm px-3 py-2 bg-white">
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="font-mono text-[11.5px] text-black/40 mb-3">{loading ? "Loading…" : `${standards.length} standard(s)`}</div>

      {standards.map((s) => <StandardCard key={s.is_number} standard={s} />)}
    </AppShell>
  );
}
