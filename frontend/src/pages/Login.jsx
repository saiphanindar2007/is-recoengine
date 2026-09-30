import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ROLE_HOME = { ADMIN: "/admin", OFFICER: "/officer", AUDITOR: "/auditor" };

const DEMO_ACCOUNTS = [
  { role: "OFFICER", email: "officer@isreco.gov.in", password: "Officer@123", label: "Procurement Officer" },
  { role: "AUDITOR", email: "auditor@isreco.gov.in", password: "Auditor@123", label: "Compliance Auditor" },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password);
      navigate(ROLE_HOME[user.role] || "/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(acc) {
    setEmail(acc.email);
    setPassword(acc.password);
  }

  return (
    <div className="min-h-screen bg-indigo-950 flex items-center justify-center px-4 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.05] pointer-events-none"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
          backgroundSize: "28px 28px",
        }}
      />
      <div className="w-full max-w-4xl grid md:grid-cols-2 bg-paper rounded-md overflow-hidden shadow-[0_25px_70px_-15px_rgba(0,0,0,0.55)] relative">
        <div className="hidden md:flex flex-col justify-between bg-indigo-900 text-white p-10 relative">
          <div
            className="absolute inset-0 opacity-[0.06] pointer-events-none"
            style={{
              backgroundImage:
                "linear-gradient(135deg, transparent 40%, white 40%, white 41%, transparent 41%)",
              backgroundSize: "22px 22px",
            }}
          />
          <div className="relative">
            <div className="w-11 h-11 rounded-full border-2 border-gold-600 flex items-center justify-center font-mono text-[12px] font-semibold mb-6 shadow-[0_0_0_4px_rgba(166,119,44,0.15)]">
              IS
            </div>
            <div className="font-display text-3xl font-medium leading-tight mb-3">
              IS-RecoEngine
            </div>
            <p className="text-white/60 text-[14px] leading-relaxed max-w-xs">
              Role-based AI recommendation platform for identifying applicable Indian Standards
              in procurement specifications.
            </p>
          </div>
          <div className="font-mono text-[11px] text-white/40 leading-relaxed relative">
            Department of Consumer Affairs<br />
            Ministry of Consumer Affairs, Food &amp; Public Distribution<br />
            Smart India Hackathon · PS 26108
          </div>
        </div>

        <div className="bg-white p-8 sm:p-10">
          <h1 className="font-display text-2xl font-medium mb-1">Sign in</h1>
          <p className="text-black/50 text-[13.5px] mb-6">Access your role-based workspace.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2.5 text-[14px] transition-shadow focus:outline-none focus:ring-2 focus:ring-indigo-800/40 focus:border-indigo-800/40"
                placeholder="you@department.gov.in"
              />
            </div>
            <div>
              <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2.5 text-[14px] transition-shadow focus:outline-none focus:ring-2 focus:ring-indigo-800/40 focus:border-indigo-800/40"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="text-seal-700 text-[13px] bg-seal-100 border border-seal-600/25 rounded-sm px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-800 hover:bg-indigo-900 disabled:opacity-60 text-white rounded-sm py-2.5 text-[14px] font-medium transition-colors shadow-sm hover:shadow-md"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-line">
            <div className="font-mono text-[10.5px] uppercase tracking-wide text-black/40 mb-2">
              Quick demo access
            </div>
            <div className="flex flex-col gap-1.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.role}
                  type="button"
                  onClick={() => fillDemo(acc)}
                  className="text-left text-[12.5px] px-3 py-2 rounded-sm border border-line hover:border-indigo-800/40 hover:bg-indigo-100/40 transition-all hover:-translate-y-px"
                >
                  <span className="font-mono text-indigo-800 font-medium">{acc.role}</span>
                  <span className="text-black/50"> — {acc.label} ({acc.email})</span>
                </button>
              ))}
              <div className="text-[11.5px] text-black/40 px-3 pt-1 leading-relaxed">
                Standards Custodian (ADMIN) access is unique per deployment — a fresh
                install generates its own credential rather than shipping a fixed one.
                See this deployment's environment configuration.
              </div>
            </div>
          </div>

          <p className="text-center text-[13px] text-black/50 mt-6">
            New procurement officer?{" "}
            <Link to="/register" className="text-indigo-800 font-medium hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
