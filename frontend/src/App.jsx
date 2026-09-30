import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Register from "./pages/Register";

import OfficerDashboard from "./pages/officer/OfficerDashboard";
import SearchPage from "./pages/officer/SearchPage";
import MySpecifications from "./pages/officer/MySpecifications";

import AdminDashboard from "./pages/admin/AdminDashboard";
import ManageStandards from "./pages/admin/ManageStandards";
import ManageUsers from "./pages/admin/ManageUsers";
import ChangeRequests from "./pages/admin/ChangeRequests";

import AuditorDashboard from "./pages/auditor/AuditorDashboard";

import StandardsCatalogue from "./pages/shared/StandardsCatalogue";
import StandardDetail from "./pages/shared/StandardDetail";
import Profile from "./pages/shared/Profile";
import AuditLog from "./pages/shared/AuditLog";
import { Forbidden, NotFound } from "./pages/shared/StatusPages";

const ROLE_HOME = { ADMIN: "/admin", OFFICER: "/officer", AUDITOR: "/auditor" };

function RoleRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={ROLE_HOME[user.role] || "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RoleRedirect />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forbidden" element={<Forbidden />} />

      <Route path="/officer" element={<ProtectedRoute roles={["OFFICER"]}><OfficerDashboard /></ProtectedRoute>} />
      <Route path="/officer/search" element={<ProtectedRoute roles={["OFFICER"]}><SearchPage /></ProtectedRoute>} />
      <Route path="/officer/specifications" element={<ProtectedRoute roles={["OFFICER"]}><MySpecifications /></ProtectedRoute>} />

      <Route path="/admin" element={<ProtectedRoute roles={["ADMIN"]}><AdminDashboard /></ProtectedRoute>} />
      <Route path="/admin/standards" element={<ProtectedRoute roles={["ADMIN"]}><ManageStandards /></ProtectedRoute>} />
      <Route path="/admin/users" element={<ProtectedRoute roles={["ADMIN"]}><ManageUsers /></ProtectedRoute>} />
      <Route path="/admin/change-requests" element={<ProtectedRoute roles={["ADMIN"]}><ChangeRequests /></ProtectedRoute>} />

      <Route path="/auditor" element={<ProtectedRoute roles={["AUDITOR"]}><AuditorDashboard /></ProtectedRoute>} />
      <Route path="/auditor/audit-log" element={<ProtectedRoute roles={["AUDITOR"]}><AuditLog /></ProtectedRoute>} />
      <Route path="/admin/audit-log" element={<ProtectedRoute roles={["ADMIN"]}><AuditLog /></ProtectedRoute>} />

      <Route path="/standards" element={<ProtectedRoute><StandardsCatalogue /></ProtectedRoute>} />
      <Route path="/standards/:isNumber" element={<ProtectedRoute><StandardDetail /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
