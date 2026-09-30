/**
 * A small, consistent loading indicator used across every list/detail page,
 * replacing the previous bare "Loading…" text with something that actually
 * reads as "the app is working" rather than "the app might be stuck."
 */
export default function LoadingState({ label = "Loading" }) {
  return (
    <div className="flex items-center gap-2.5 py-10 justify-center text-black/40">
      <span className="relative flex h-2.5 w-2.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-800/40" />
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-800/70" />
      </span>
      <span className="font-mono text-[12.5px] tracking-wide">{label}…</span>
    </div>
  );
}
