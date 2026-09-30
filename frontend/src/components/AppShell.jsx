import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  Search, LayoutDashboard, FileStack, ShieldCheck, Users,
  FlagTriangleRight, BarChart3, LogOut, BookMarked, ScrollText,
} from "lucide-react";

const NAV_BY_ROLE = {
  OFFICER: [
    { to: "/officer", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/officer/search", label: "Recommend Standards", icon: Search },
    { to: "/officer/specifications", label: "My Specifications", icon: FileStack },
    { to: "/standards", label: "Standards Catalogue", icon: BookMarked },
  ],
  ADMIN: [
    { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/admin/standards", label: "Manage Standards", icon: ShieldCheck },
    { to: "/admin/change-requests", label: "Change Requests", icon: FlagTriangleRight },
    { to: "/admin/users", label: "Manage Users", icon: Users },
    { to: "/admin/audit-log", label: "Audit Log", icon: ScrollText },
    { to: "/standards", label: "Standards Catalogue", icon: BookMarked },
  ],
  AUDITOR: [
    { to: "/auditor", label: "Analytics Dashboard", icon: BarChart3, end: true },
    { to: "/auditor/audit-log", label: "Audit Log", icon: ScrollText },
    { to: "/standards", label: "Standards Catalogue", icon: BookMarked },
  ],
};

const ROLE_LABEL = {
  ADMIN: "Standards Custodian",
  OFFICER: "Procurement Officer",
  AUDITOR: "Compliance Auditor",
};

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const nav = NAV_BY_ROLE[user?.role] || [];

  function handleLogout() {
    logout().then(() => navigate("/login"));
  }

  return (
    <div className="min-h-screen flex bg-paper">
      <aside className="w-64 shrink-0 bg-indigo-900 text-white flex flex-col shadow-[4px_0_24px_-8px_rgba(0,0,0,0.35)] z-10">
        <div className="px-5 py-5 border-b border-white/10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full border-2 border-gold-600 flex items-center justify-center font-mono text-[11px] font-semibold shadow-[0_0_0_3px_rgba(166,119,44,0.15)]">
            IS
          </div>
          <div>
            <div className="font-display font-semibold text-[16px] leading-tight">IS-RecoEngine</div>
            <div className="font-mono text-[10px] text-white/50">SIH PS 26108</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 pl-3.5 pr-3 py-2.5 rounded-sm text-[13.5px] transition-all ${
                  isActive
                    ? "bg-white/[0.08] text-white font-medium"
                    : "text-white/60 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`absolute left-0 top-1.5 bottom-1.5 w-[2.5px] rounded-full transition-colors ${
                      isActive ? "bg-gold-600" : "bg-transparent"
                    }`}
                  />
                  <Icon size={16} strokeWidth={2} className={isActive ? "text-gold-600" : "opacity-80 group-hover:opacity-100"} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-white/10">
          <NavLink
            to="/profile"
            className="flex items-center gap-3 px-3 py-2 rounded-sm text-[13px] text-white/70 hover:bg-white/5 hover:text-white mb-1 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-gold-600 flex items-center justify-center font-mono text-[11px] font-semibold text-white shrink-0">
              {user?.full_name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="truncate">
              <div className="truncate">{user?.full_name}</div>
              <div className="text-[10px] text-white/40 font-mono">{ROLE_LABEL[user?.role]}</div>
            </div>
          </NavLink>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-sm text-[13px] text-white/60 hover:bg-seal-600/20 hover:text-white transition-colors"
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <div className="max-w-6xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
