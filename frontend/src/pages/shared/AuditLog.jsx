import { useEffect, useState } from "react";
import client from "../../api/client";
import AppShell from "../../components/AppShell";
import LoadingState from "../../components/LoadingState";
import Badge from "../../components/Badge";
import ExportCsvButton from "../../components/ExportCsvButton";

const ACTION_TONE = {
  STANDARD_CREATE: "green",
  STANDARD_UPDATE: "gold",
  STANDARD_DELETE: "seal",
  USER_ACTIVATE: "green",
  USER_DEACTIVATE: "seal",
  USER_REGISTER: "default",
  CHANGE_REQUEST_RAISED: "gold",
  CHANGE_REQUEST_RESOLVED: "green",
};

const AUDIT_LOG_CSV_COLUMNS = [
  { key: "created_at", label: "Timestamp (ISO)", value: (r) => r.created_at },
  { key: "created_at_local", label: "Timestamp", value: (r) => new Date(r.created_at).toLocaleString() },
  { key: "action", label: "Action" },
  { key: "target_type", label: "Target Type" },
  { key: "target_id", label: "Target ID" },
  { key: "actor_email", label: "Actor Email" },
  { key: "actor_role", label: "Actor Role" },
  { key: "detail", label: "Detail (JSON)", value: (r) => (r.detail && Object.keys(r.detail).length ? JSON.stringify(r.detail) : "") },
];

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    const params = actionFilter ? { action: actionFilter } : {};
    client.get("/api/audit-logs", { params }).then((res) => setLogs(res.data)).finally(() => setLoading(false));
  }, [actionFilter]);

  return (
    <AppShell>
      <div className="mb-6">
        <div className="font-mono text-[12px] text-seal-700 mb-1">GOVERNANCE</div>
        <h1 className="font-display text-3xl font-medium mb-2">Audit Log</h1>
        <p className="text-black/55 text-[14.5px]">
          Append-only record of every administrative mutation on the platform. Nothing here is
          ever edited or deleted — this is a write-once trail, not a mutable log table.
        </p>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}
          className="font-mono text-[12.5px] border border-line rounded-sm px-3 py-2 bg-white">
          <option value="">All actions</option>
          {Object.keys(ACTION_TONE).map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <ExportCsvButton
          filename={`audit-log${actionFilter ? `-${actionFilter.toLowerCase()}` : ""}-${new Date().toISOString().slice(0, 10)}.csv`}
          rows={logs}
          columns={AUDIT_LOG_CSV_COLUMNS}
          label={`Export CSV${logs.length ? ` (${logs.length})` : ""}`}
        />
      </div>

      {loading ? (
        <LoadingState />
      ) : logs.length === 0 ? (
        <div className="font-mono text-[13px] text-black/45 border border-dashed border-line rounded-sm p-8 text-center">
          No audit entries yet.
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="bg-white border border-line rounded-sm px-4 py-3">
              <div className="flex items-center justify-between gap-3 flex-wrap mb-1">
                <div className="flex items-center gap-2">
                  <Badge tone={ACTION_TONE[log.action] || "neutral"}>{log.action}</Badge>
                  <span className="text-[12.5px] text-black/55">
                    {log.target_type}{log.target_id ? ` · ${log.target_id}` : ""}
                  </span>
                </div>
                <span className="font-mono text-[10.5px] text-black/40">{new Date(log.created_at).toLocaleString()}</span>
              </div>
              <div className="text-[12px] text-black/50">
                by <span className="font-mono">{log.actor_email || "unknown"}</span> ({log.actor_role || "—"})
              </div>
              {log.detail && Object.keys(log.detail).length > 0 && (
                <pre className="mt-2 text-[11px] bg-paper rounded-sm px-3 py-2 overflow-x-auto text-black/60">
                  {JSON.stringify(log.detail, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
