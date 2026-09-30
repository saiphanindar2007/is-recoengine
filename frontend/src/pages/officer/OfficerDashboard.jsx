import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import AppShell from "../../components/AppShell";
import { Search, FileStack, ArrowRight } from "lucide-react";

export default function OfficerDashboard() {
  const { user } = useAuth();
  const [specs, setSpecs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get("/api/specifications").then((res) => setSpecs(res.data)).finally(() => setLoading(false));
  }, []);

  const drafts = specs.filter((s) => s.status === "DRAFT").length;
  const finalized = specs.filter((s) => s.status === "FINALIZED").length;

  return (
    <AppShell>
      <div className="mb-8">
        <div className="font-mono text-[12px] text-seal-700 mb-1">PROCUREMENT WORKSPACE</div>
        <h1 className="font-display text-3xl font-medium mb-1">Welcome, {user?.full_name?.split(" ")[0]}</h1>
        <p className="text-black/55 text-[14.5px]">{user?.department} · {user?.designation}</p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4 mb-8">
        <StatCard label="Draft specifications" value={loading ? "—" : drafts} />
        <StatCard label="Finalized specifications" value={loading ? "—" : finalized} />
        <StatCard label="Total saved" value={loading ? "—" : specs.length} />
      </div>

      <div className="grid md:grid-cols-2 gap-5 mb-10">
        <Link to="/officer/search" className="group bg-indigo-900 text-white rounded-sm p-6 flex flex-col justify-between hover:bg-indigo-800 transition-colors">
          <div>
            <Search size={22} className="mb-4 text-gold-600" />
            <div className="font-display text-xl font-medium mb-1.5">Recommend Standards</div>
            <p className="text-white/60 text-[13.5px] leading-relaxed">
              Describe a product or tender clause in plain language and get the applicable
              Indian Standard, its allied network, and certification requirements.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-gold-600 text-[13px] font-medium mt-5">
            Start a search <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
          </div>
        </Link>

        <Link to="/officer/specifications" className="group bg-white border border-line rounded-sm p-6 flex flex-col justify-between hover:border-indigo-800/40 transition-colors">
          <div>
            <FileStack size={22} className="mb-4 text-indigo-800" />
            <div className="font-display text-xl font-medium mb-1.5">My Specifications</div>
            <p className="text-black/55 text-[13.5px] leading-relaxed">
              Review, edit, and finalize the tender specification packages you've built from
              recommended standards.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-indigo-800 text-[13px] font-medium mt-5">
            View workspace <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
          </div>
        </Link>
      </div>

      {!loading && specs.length > 0 && (
        <div>
          <h2 className="font-mono text-[12px] uppercase tracking-wide text-black/45 border-b border-line pb-2 mb-4">
            Recently updated
          </h2>
          <div className="space-y-2">
            {specs.slice(0, 5).map((s) => (
              <Link key={s.id} to="/officer/specifications" className="flex items-center justify-between bg-white border border-line rounded-sm px-4 py-3 hover:border-indigo-800/40 transition-colors">
                <div>
                  <div className="text-[14px] font-medium">{s.title}</div>
                  <div className="text-[12px] text-black/45">{s.standard_numbers.length} standard(s) · updated {new Date(s.updated_at).toLocaleDateString()}</div>
                </div>
                <span className={`font-mono text-[10.5px] px-2 py-1 rounded-sm border ${s.status === "FINALIZED" ? "bg-emerald-50 text-emerald-700 border-emerald-600/25" : "bg-gold-100 text-gold-700 border-gold-600/25"}`}>
                  {s.status}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </AppShell>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="bg-white border border-line rounded-sm p-5">
      <div className="font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-2">{label}</div>
      <div className="font-display text-3xl font-medium text-indigo-900">{value}</div>
    </div>
  );
}
