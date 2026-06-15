import { Outlet, NavLink } from "react-router-dom";
import { LayoutDashboard, ScanLine, BookOpen, LogOut } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col gap-1 border-r border-gray-800 bg-gray-900 p-4">
        <div className="mb-6 px-2">
          <h1 className="text-lg font-bold tracking-tight text-white">CardTrackr</h1>
          <p className="text-xs text-gray-500">{user?.username}</p>
        </div>

        <NavItem to="/" icon={<LayoutDashboard size={16} />} label="Dashboard" />
        <NavItem to="/scan" icon={<ScanLine size={16} />} label="Scan Cards" />
        <NavItem to="/collection" icon={<BookOpen size={16} />} label="Collection" />

        <button
          onClick={logout}
          className="mt-auto flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}

function NavItem({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
          isActive
            ? "bg-blue-600 text-white"
            : "text-gray-400 hover:bg-gray-800 hover:text-white"
        }`
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
