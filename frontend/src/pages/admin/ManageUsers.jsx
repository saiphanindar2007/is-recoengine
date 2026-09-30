import { useEffect, useState } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingState from "../../components/LoadingState";
import Badge from "../../components/Badge";
import { useAuth } from "../../context/AuthContext";
import { UserPlus } from "lucide-react";

const EMPTY_FORM = { full_name: "", email: "", password: "", role: "OFFICER", department: "", designation: "" };

export default function ManageUsers() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    client.get("/api/users").then((res) => setUsers(res.data)).finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function toggle(u) {
    const action = u.is_active ? "deactivate" : "activate";
    await client.put(`/api/users/${u.id}/${action}`);
    load();
  }

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await client.post("/api/users", form);
      setCreating(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not create the account.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell>
      <div className="flex items-start justify-between flex-wrap gap-3 mb-6">
        <div>
          <div className="font-mono text-[12px] text-seal-700 mb-1">STANDARDS CUSTODIAN</div>
          <h1 className="font-display text-3xl font-medium mb-1">Manage Users</h1>
          <p className="text-black/55 text-[14.5px] max-w-xl">
            All registered accounts. Public self-registration only creates Procurement Officer
            accounts — Standards Custodian and Compliance Auditor accounts can only be created
            here, by an existing custodian.
          </p>
        </div>
        {!creating && (
          <button onClick={() => setCreating(true)}
            className="flex items-center gap-1.5 bg-indigo-800 hover:bg-indigo-900 text-white px-4 py-2.5 rounded-sm text-[13.5px] font-medium">
            <UserPlus size={15} /> Create Staff Account
          </button>
        )}
      </div>

      {creating && (
        <form onSubmit={handleCreate} className="bg-white border border-indigo-800/25 rounded-sm p-5 mb-6 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Full name">
              <input required value={form.full_name} onChange={(e) => update("full_name", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </Field>
            <Field label="Email">
              <input type="email" required value={form.email} onChange={(e) => update("email", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </Field>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Temporary password">
              <input type="password" required minLength={8} value={form.password} onChange={(e) => update("password", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </Field>
            <Field label="Role">
              <select value={form.role} onChange={(e) => update("role", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] bg-white focus:outline-none focus:ring-2 focus:ring-indigo-800/40">
                <option value="OFFICER">Procurement Officer</option>
                <option value="AUDITOR">Compliance Auditor</option>
                <option value="ADMIN">Standards Custodian</option>
              </select>
            </Field>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Department">
              <input value={form.department} onChange={(e) => update("department", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </Field>
            <Field label="Designation">
              <input value={form.designation} onChange={(e) => update("designation", e.target.value)}
                className="w-full border border-line rounded-sm px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-indigo-800/40" />
            </Field>
          </div>
          {error && <div className="text-seal-700 text-[13px] bg-seal-100 border border-seal-600/25 rounded-sm px-3 py-2">{error}</div>}
          <div className="flex gap-2">
            <button type="submit" disabled={submitting}
              className="bg-indigo-800 hover:bg-indigo-900 disabled:opacity-60 text-white px-5 py-2 rounded-sm text-[13.5px] font-medium">
              {submitting ? "Creating…" : "Create account"}
            </button>
            <button type="button" onClick={() => { setCreating(false); setForm(EMPTY_FORM); }} className="text-black/50 text-[13.5px] px-3">
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <LoadingState />
      ) : (
        <div className="bg-white border border-line rounded-sm overflow-hidden">
          <table className="w-full text-[13.5px]">
            <thead>
              <tr className="bg-paper border-b border-line font-mono text-[10.5px] uppercase tracking-wide text-black/45">
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Email</th>
                <th className="text-left px-4 py-3">Role</th>
                <th className="text-left px-4 py-3">Department</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3 font-medium">{u.full_name}</td>
                  <td className="px-4 py-3 text-black/60 font-mono text-[12.5px]">{u.email}</td>
                  <td className="px-4 py-3"><Badge>{u.role}</Badge></td>
                  <td className="px-4 py-3 text-black/60">{u.department || "—"}</td>
                  <td className="px-4 py-3">
                    <Badge tone={u.is_active ? "green" : "seal"}>{u.is_active ? "ACTIVE" : "DEACTIVATED"}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.id !== me.id && (
                      <button onClick={() => toggle(u)} className="text-[12.5px] text-indigo-800 hover:underline">
                        {u.is_active ? "Deactivate" : "Activate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block font-mono text-[10.5px] uppercase tracking-wide text-black/45 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
