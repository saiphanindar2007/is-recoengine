import { useEffect, useState } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import ExportCsvButton from "../../components/ExportCsvButton";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, CartesianGrid,
} from "recharts";

const COLORS = ["#1F3D5C", "#A6772C", "#8A1F1F", "#2A4F73", "#5C6470", "#B3AB90", "#6E1818", "#8A5F1F"];

const CATEGORY_CSV_COLUMNS = [
  { key: "category", label: "Category" },
  { key: "count", label: "Standards" },
];

const TOP_MATCHED_CSV_COLUMNS = [
  { key: "is_number", label: "IS Number" },
  { key: "count", label: "Times Recommended" },
];

const RECENT_QUERIES_CSV_COLUMNS = [
  { key: "created_at", label: "Timestamp" },
  { key: "query_text", label: "Query Text" },
  { key: "top_match_is_number", label: "Top Match" },
  { key: "top_match_score", label: "Top Match Score" },
  { key: "source", label: "Source" },
];

const todayStamp = () => new Date().toISOString().slice(0, 10);

export default function AuditorDashboard() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    client.get("/api/analytics/summary").then((res) => setSummary(res.data));
  }, []);

  if (!summary) {
    return <AppShell><div className="font-mono text-[13px] text-black/40">Loading analytics…</div></AppShell>;
  }

  return (
    <AppShell>
      <div className="mb-8">
        <div className="font-mono text-[12px] text-seal-700 mb-1">COMPLIANCE AUDITOR · READ-ONLY</div>
        <h1 className="font-display text-3xl font-medium mb-1">Platform Analytics</h1>
        <p className="text-black/55 text-[14.5px]">System-wide usage across procurement officers and the standards catalogue.</p>
      </div>

      <div className="grid sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
        <Stat label="Standards" value={summary.total_standards} />
        <Stat label="Users" value={summary.total_users} />
        <Stat label="Total queries" value={summary.total_queries} />
        <Stat label="Queries (7 days)" value={summary.queries_last_7_days} />
        <Stat label="Open change requests" value={summary.open_change_requests} tone={summary.open_change_requests > 0 ? "seal" : undefined} />
      </div>

      <div className="flex items-center gap-2 mb-10 font-mono text-[11.5px]">
        <span className={`px-2 py-1 rounded-sm border ${summary.embeddings_active ? "border-emerald-600/30 text-emerald-700 bg-emerald-50" : "border-line text-black/45"}`}>
          {summary.embeddings_active ? "Hybrid semantic search active (TF-IDF + embeddings)" : "TF-IDF matching only — dense embeddings not loaded on this deployment"}
        </span>
        {summary.outdated_standards_count > 0 && (
          <span className="px-2 py-1 rounded-sm border border-seal-600/25 text-seal-700 bg-seal-100">
            {summary.outdated_standards_count} standard(s) marked superseded
          </span>
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-10">
        <div className="bg-white border border-line rounded-sm p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="font-mono text-[11.5px] uppercase tracking-wide text-black/45">Standards by Category</h2>
            <ExportCsvButton
              filename={`standards-by-category-${todayStamp()}.csv`}
              rows={summary.top_categories}
              columns={CATEGORY_CSV_COLUMNS}
            />
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={summary.top_categories} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={95}
                label={({ category, count }) => `${category}: ${count}`}>
                {summary.top_categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white border border-line rounded-sm p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="font-mono text-[11.5px] uppercase tracking-wide text-black/45">Most Recommended Standards</h2>
            <ExportCsvButton
              filename={`most-recommended-standards-${todayStamp()}.csv`}
              rows={summary.top_matched_standards}
              columns={TOP_MATCHED_CSV_COLUMNS}
            />
          </div>
          {summary.top_matched_standards.length === 0 ? (
            <div className="font-mono text-[12.5px] text-black/40 h-[280px] flex items-center justify-center">No queries logged yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={summary.top_matched_standards} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E1DCCC" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="is_number" width={130} tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }} />
                <Tooltip />
                <Bar dataKey="count" fill="#1F3D5C" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="bg-white border border-line rounded-sm p-5">
        <div className="flex items-center justify-between gap-3 mb-4">
          <h2 className="font-mono text-[11.5px] uppercase tracking-wide text-black/45">Recent Query Activity</h2>
          <ExportCsvButton
            filename={`recent-query-activity-${todayStamp()}.csv`}
            rows={summary.recent_queries}
            columns={RECENT_QUERIES_CSV_COLUMNS}
          />
        </div>
        {summary.recent_queries.length === 0 ? (
          <div className="font-mono text-[12.5px] text-black/40">No activity yet.</div>
        ) : (
          <div className="divide-y divide-line">
            {summary.recent_queries.map((q, i) => (
              <div key={i} className="py-3 flex items-center justify-between gap-3 flex-wrap">
                <div className="text-[13px]">{q.query_text}</div>
                <div className="flex items-center gap-3 shrink-0">
                  {q.top_match_is_number && (
                    <span className="font-mono text-[11.5px] text-indigo-800">{q.top_match_is_number}</span>
                  )}
                  <span className="font-mono text-[10.5px] text-black/40">{new Date(q.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="bg-white border border-line rounded-sm p-4">
      <div className="font-mono text-[10px] uppercase tracking-wide text-black/45 mb-1.5">{label}</div>
      <div className={`font-display text-2xl font-medium ${tone === "seal" ? "text-seal-700" : "text-indigo-900"}`}>{value}</div>
    </div>
  );
}
