export default function Badge({ children, tone = "default" }) {
  const tones = {
    default: "bg-indigo-100 text-indigo-900 border-indigo-800/15",
    gold: "bg-gold-100 text-gold-700 border-gold-600/25",
    seal: "bg-seal-100 text-seal-700 border-seal-600/25",
    neutral: "bg-black/5 text-black/60 border-black/10",
    green: "bg-emerald-50 text-emerald-700 border-emerald-600/25",
  };
  return (
    <span
      className={`inline-flex items-center font-mono text-[11px] leading-none px-2 py-1 rounded-sm border ${tones[tone] || tones.default}`}
    >
      {children}
    </span>
  );
}
