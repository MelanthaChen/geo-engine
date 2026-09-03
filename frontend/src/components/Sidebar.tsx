import {
  FileSearch,
  BrainCircuit,
  FlaskConical,
  FlaskRound,
  History,
  LayoutDashboard,
  PenLine,
  Send,
  Settings,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { Separator } from "../../@/components/ui/separator";

import { PropertySelector } from "@/components/PropertySelector";
import { useProperty } from "@/contexts/PropertyContext";

const navigationItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Website Audit", href: "/audit", icon: FileSearch },
  { label: "Experiment Lab", href: "/experiments", icon: FlaskRound },
  { label: "GEO Predictor", href: "/predictor", icon: BrainCircuit },
  { label: "Social Media Track", href: "/content", icon: PenLine },
  { label: "Publishing Queue", href: "/publishing", icon: Send },
  { label: "Citation Tests", href: "/citations", icon: FlaskConical },
  { label: "Content History", href: "/history", icon: History },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const { activeProperty } = useProperty();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 p-4">
        <PropertySelector />
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
            {activeProperty?.brand_name || "Category-driven GEO"}
          </p>
          <Separator className="my-3" />
          <p className="mt-1 text-xs text-zinc-500">
            Changing property scopes dashboard data, history, and experiments.
          </p>
        </div>
      </div>
    </aside>
  );
}
