/**
 * Minimal, dependency-free CSV export helper used by the Auditor-facing
 * pages (Analytics Dashboard, Audit Log). Deliberately hand-rolled instead
 * of pulling in a CSV library — the format needed here (flat rows of
 * primitives) doesn't need one, and this keeps the frontend's dependency
 * footprint exactly as it was.
 *
 * Usage:
 *   exportToCsv("audit-log.csv", rows, [
 *     { key: "created_at", label: "Timestamp" },
 *     { key: "action",     label: "Action" },
 *   ]);
 *
 * `columns` is optional — if omitted, the keys of the first row are used
 * (in that row's own key order) and turned into Title Case headers.
 */

function escapeCsvCell(value) {
  if (value === null || value === undefined) return "";
  const str = typeof value === "object" ? JSON.stringify(value) : String(value);
  // RFC 4180: any field containing a comma, double quote, or newline must be
  // quoted, and embedded double quotes must be doubled.
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function titleCase(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function rowsToCsv(rows, columns) {
  if (!rows || rows.length === 0) return "";
  const cols = columns || Object.keys(rows[0]).map((key) => ({ key, label: titleCase(key) }));

  const header = cols.map((c) => escapeCsvCell(c.label)).join(",");
  const lines = rows.map((row) =>
    cols.map((c) => escapeCsvCell(typeof c.value === "function" ? c.value(row) : row[c.key])).join(",")
  );
  // CRLF line endings, per RFC 4180 — opens cleanly in Excel on Windows/macOS,
  // not just in text editors.
  return [header, ...lines].join("\r\n");
}

/**
 * Builds a CSV string from `rows` (+ optional `columns` spec) and triggers a
 * browser download named `filename`. No server round-trip — the auditor
 * exports exactly the rows currently loaded/filtered on screen.
 */
export function exportToCsv(filename, rows, columns) {
  if (!rows || rows.length === 0) return false;
  const csv = rowsToCsv(rows, columns);
  // A UTF-8 BOM so Excel (which otherwise guesses the wrong encoding for
  // non-ASCII text — relevant here since standard titles/scopes and user
  // names may include non-ASCII characters) renders the file correctly.
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}
