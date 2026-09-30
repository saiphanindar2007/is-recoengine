import { useAuth } from "../../context/AuthContext";
import AppShell from "../../components/AppShell";
import Badge from "../../components/Badge";

const ROLE_LABEL = {
  ADMIN: "Standards Custodian (BIS / DoCA)",
  OFFICER: "Procurement Officer",
  AUDITOR: "Compliance Auditor",
};

export default function Profile() {
  const { user } = useAuth();
  return (
    <AppShell>
      <div className="mb-6">
        <div className="font-mono text-[12px] text-seal-700 mb-1">ACCOUNT</div>
        <h1 className="font-display text-3xl font-medium mb-1">Profile</h1>
      </div>

      <div className="bg-white border border-line rounded-sm p-7 max-w-lg">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-full bg-gold-600 flex items-center justify-center font-mono text-[20px] font-semibold text-white">
            {user?.full_name?.[0]?.toUpperCase()}
          </div>
          <div>
            <div className="font-display text-xl font-medium">{user?.full_name}</div>
            <Badge>{ROLE_LABEL[user?.role]}</Badge>
          </div>
        </div>

        <div className="space-y-4 text-[13.5px]">
          <Row label="Email" value={user?.email} />
          <Row label="Department" value={user?.department || "—"} />
          <Row label="Designation" value={user?.designation || "—"} />
          <Row label="Account created" value={user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"} />
        </div>
      </div>
    </AppShell>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between border-b border-line pb-3">
      <span className="font-mono text-[10.5px] uppercase tracking-wide text-black/45">{label}</span>
      <span>{value}</span>
    </div>
  );
}
