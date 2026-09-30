import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import { ShieldCheck, Users, FlagTriangleRight, ArrowRight } from "lucide-react";

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    client.get("/api/analytics/summary").then((res) => setSummary(res.data));
  }, []);

  return (
    <AppShell>
      <div className="mb-8">
        <div className="font-mono text-[12px] text-seal-700 mb-1">STANDARDS CUSTODIAN</div>
        <h1 className="font-display text-3xl font-medium mb-1">Catalogue Administration</h1>
        <p className="text-black/55 text-[14.5px]">Manage the live Indian Standards corpus, users, and review flagged entries.</p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4 mb-10">
        <Stat label="Published standards" value={summary?.total_standards ?? "—"} />
        <Stat label="Registered users" value={summary?.total_users ?? "—"} />
        <Stat label="Open change requests" value={summary?.open_change_requests ?? "—"} tone={summary?.open_change_requests > 0 ? "seal" : undefined} />
      </div>

      {summary && (
        <div className="flex items-center gap-2 mb-8 font-mono text-[11.5px]">
          <span className={`px-2 py-1 rounded-sm border ${summary.embeddings_active ? "border-emerald-600/30 text-emerald-700 bg-emerald-50" : "border-line text-black/45"}`}>
            {summary.embeddings_active ? "Hybrid semantic search active (TF-IDF + embeddings)" : "TF-IDF matching only — dense embeddings not loaded on this deployment"}
          </span>
          {summary.outdated_standards_count > 0 && (
            <span className="px-2 py-1 rounded-sm border border-seal-600/25 text-seal-700 bg-seal-100">
              {summary.outdated_standards_count} standard(s) marked superseded
            </span>
          )}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-5">
        <AdminTile to="/admin/standards" icon={ShieldCheck} title="Manage Standards"
          desc="Add, edit, publish or withdraw standards. Every change instantly rebuilds the live semantic index." />
        <AdminTile to="/admin/change-requests" icon={FlagTriangleRight} title="Change Requests"
          desc="Review standards flagged by procurement officers as outdated or incorrect." accent="seal" />
        <AdminTile to="/admin/users" icon={Users} title="Manage Users"
          desc="View registered accounts across roles and deactivate accounts if required." />
      </div>
    </AppShell>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="bg-white border border-line rounded-sm p-5">
      <div className="font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-2">{label}</div>
      <div className={`font-display text-3xl font-medium ${tone === "seal" ? "text-seal-700" : "text-indigo-900"}`}>{value}</div>
    </div>
  );
}

function AdminTile({ to, icon: Icon, title, desc, accent }) {
  return (
    <Link to={to} className="group bg-white border border-line rounded-sm p-6 flex flex-col justify-between hover:border-indigo-800/40 transition-colors">
      <div>
        <Icon size={22} className={`mb-4 ${accent === "seal" ? "text-seal-600" : "text-indigo-800"}`} />
        <div className="font-display text-lg font-medium mb-1.5">{title}</div>
        <p className="text-black/55 text-[13px] leading-relaxed">{desc}</p>
      </div>
      <div className="flex items-center gap-1.5 text-indigo-800 text-[12.5px] font-medium mt-5">
        Open <ArrowRight size={13} className="group-hover:translate-x-0.5 transition-transform" />
      </div>
    </Link>
  );
}
