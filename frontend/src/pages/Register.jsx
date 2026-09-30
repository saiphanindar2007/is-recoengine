import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "", email: "", password: "", department: "", designation: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // Public self-registration always creates an OFFICER account — this is
      // enforced server-side too (the API rejects any other role here), so
      // there's no elevated-role option to offer in this form at all.
      const user = await register({ ...form, role: "OFFICER" });
      navigate("/officer");
    } catch (err) {
      setError(err?.response?.data?.detail || "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-indigo-950 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg bg-white rounded-sm p-8 sm:p-10 shadow-2xl">
        <h1 className="font-display text-2xl font-medium mb-1">Create an account</h1>
        <p className="text-black/50 text-[13.5px] mb-6">
          Self-registration creates a Procurement Officer account. Standards Custodian or
          Compliance Auditor access is granted by an existing Standards Custodian from
          "Manage Users" — it can't be self-selected here.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">Full name</label>
              <input required value={form.full_name} onChange={(e) => update("full_name", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </div>
            <div>
              <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">Email</label>
              <input type="email" required value={form.email} onChange={(e) => update("email", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </div>
          </div>

          <div>
            <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">Password</label>
            <input type="password" required minLength={8} value={form.password} onChange={(e) => update("password", e.target.value)}
              className="w-full border border-line rounded-sm px-3 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            <p className="text-[11.5px] text-black/40 mt-1">At least 8 characters, with a letter and a digit.</p>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">Department</label>
              <input value={form.department} onChange={(e) => update("department", e.target.value)}
                placeholder="e.g. CPWD, State PWD"
                className="w-full border border-line rounded-sm px-3 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </div>
            <div>
              <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">Designation</label>
              <input value={form.designation} onChange={(e) => update("designation", e.target.value)}
                placeholder="e.g. Executive Engineer"
                className="w-full border border-line rounded-sm px-3 py-2.5 text-[14px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </div>
          </div>

          {error && (
            <div className="text-seal-700 text-[13px] bg-seal-100 border border-seal-600/25 rounded-sm px-3 py-2">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading}
            className="w-full bg-indigo-800 hover:bg-indigo-900 disabled:opacity-60 text-white rounded-sm py-2.5 text-[14px] font-medium transition-colors">
            {loading ? "Creating account…" : "Create Officer account"}
          </button>
        </form>

        <p className="text-center text-[13px] text-black/50 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-800 font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
