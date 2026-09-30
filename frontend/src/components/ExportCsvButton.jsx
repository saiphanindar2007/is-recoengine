import { Download } from "lucide-react";
import { exportToCsv } from "../utils/csv";

/**
 * A small, consistently-styled "Export CSV" action. Disabled (not hidden)
 * when there's nothing to export, so the control doesn't jump around the
 * layout as data loads in.
 */
export default function ExportCsvButton({ filename, rows, columns, label = "Export CSV" }) {
  const disabled = !rows || rows.length === 0;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => exportToCsv(filename, rows, columns)}
      title={disabled ? "Nothing to export yet" : `Download ${rows.length} row(s) as CSV`}
      className="inline-flex items-center gap-1.5 font-mono text-[11.5px] uppercase tracking-wide px-2.5 py-1.5 rounded-sm border border-line text-black/55 hover:text-indigo-800 hover:border-indigo-800/40 hover:bg-indigo-100/40 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:border-line disabled:hover:text-black/55 transition-colors"
    >
      <Download size={13} strokeWidth={2} />
      {label}
    </button>
  );
}
