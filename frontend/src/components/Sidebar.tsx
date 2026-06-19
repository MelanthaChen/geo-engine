import {
  BarChart3,
  BookOpenText,
  FlaskConical,
  History,
  LayoutDashboard,
  PenLine,
  Send,
  Settings,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const navigationItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Content Generation", href: "/content", icon: PenLine },
  { label: "Publishing Queue", href: "/publishing", icon: Send },
  { label: "Visibility Tracking", href: "/visibility", icon: BarChart3 },
  { label: "Citation Tests", href: "/citations", icon: FlaskConical },
  { label: "Content History", href: "/history", icon: History },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="flex h-20 items-center gap-3 border-b border-zinc-800 px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-900">
          <BookOpenText className="h-5 w-5 text-blue-400" />
        </div>

        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-zinc-500">
            GEO Engine
          </p>
          <h1 className="text-lg font-semibold text-zinc-50">
            Research Console
          </h1>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-5">
        {navigationItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            end={item.href === "/"}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition",
                isActive
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-400 hover:bg-zinc-900/70 hover:text-zinc-100",
              ].join(" ")
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-zinc-800 p-4">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
            Workspace
          </p>
          <p className="mt-2 text-sm font-semibold text-zinc-100">
            Category-driven GEO
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            FAQ discovery, publishing, and citation experiments.
          </p>
        </div>
      </div>
    </aside>
  );
}
