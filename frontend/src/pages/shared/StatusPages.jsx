import { Link } from "react-router-dom";
import { ShieldAlert, SearchX } from "lucide-react";

export function Forbidden() {
  return (
    <Centered icon={<ShieldAlert size={40} className="text-seal-600" />} title="Access restricted"
      desc="Your role does not have permission to view this page." />
  );
}

export function NotFound() {
  return (
    <Centered icon={<SearchX size={40} className="text-indigo-800" />} title="Page not found"
      desc="The page you're looking for doesn't exist." />
  );
}

function Centered({ icon, title, desc }) {
  return (
    <div className="min-h-screen bg-paper flex items-center justify-center px-4">
      <div className="text-center max-w-sm">
        <div className="flex justify-center mb-4">{icon}</div>
        <h1 className="font-display text-2xl font-medium mb-2">{title}</h1>
        <p className="text-black/55 text-[14px] mb-6">{desc}</p>
        <Link to="/" className="text-indigo-800 font-medium text-[14px] hover:underline">← Back home</Link>
      </div>
    </div>
  );
}
