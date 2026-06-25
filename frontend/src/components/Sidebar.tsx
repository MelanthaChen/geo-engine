import {
  ChevronDown,
  FileSearch,
  FlaskConical,
  History,
  LayoutDashboard,
  Plus,
  PenLine,
  Send,
  Settings,
} from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router-dom";

import { Button } from "../../@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../@/components/ui/dialog";

import { useProperty } from "@/contexts/PropertyContext";

const navigationItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Website Audit", href: "/audit", icon: FileSearch },
  { label: "Social Media Track", href: "/content", icon: PenLine },
  { label: "Publishing Queue", href: "/publishing", icon: Send },
  { label: "Citation Tests", href: "/citations", icon: FlaskConical },
  { label: "Content History", href: "/history", icon: History },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const {
    activeProperty,
    addProperty,
    loading,
    properties,
    setActiveProperty,
  } = useProperty();
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addForm, setAddForm] = useState({
    name: "",
    brand_name: "",
    domain: "",
    description: "",
  });
  const [propertyError, setPropertyError] = useState("");
  const [creatingProperty, setCreatingProperty] = useState(false);

  async function handleAddProperty() {
    if (
      !addForm.name.trim() ||
      !addForm.brand_name.trim() ||
      !addForm.domain.trim()
    ) {
      setPropertyError("Property name, brand name, and website URL are required.");
      return;
    }

    try {
      setCreatingProperty(true);
      setPropertyError("");
      await addProperty({
        name: addForm.name.trim(),
        domain: addForm.domain.trim(),
        brand_name: addForm.brand_name.trim(),
        description: addForm.description.trim() || null,
      });

      setAddForm({
        name: "",
        brand_name: "",
        domain: "",
        description: "",
      });
      setAddDialogOpen(false);
      setSelectorOpen(false);
    } catch (error) {
      console.error(error);
      setPropertyError("Failed to create property.");
    } finally {
      setCreatingProperty(false);
    }
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="relative border-b border-zinc-800 p-4">
        <button
          className="flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-3 text-left transition hover:border-zinc-700"
          onClick={() => setSelectorOpen((isOpen) => !isOpen)}
          type="button"
        >
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-zinc-50">
              {loading
                ? "Loading properties..."
                : activeProperty?.name || "Select property"}
            </span>
            <span className="mt-1 block truncate text-xs text-zinc-500">
              {activeProperty?.domain || "No active domain"}
            </span>
          </span>

          <ChevronDown className="h-4 w-4 shrink-0 text-zinc-500" />
        </button>

        {selectorOpen && (
          <div className="absolute left-4 right-4 top-[76px] z-50 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950 shadow-2xl">
            <div className="max-h-72 overflow-y-auto py-2">
              {properties.map((property) => (
                <button
                  key={property.id}
                  className={[
                    "block w-full px-3 py-3 text-left transition hover:bg-zinc-900",
                    activeProperty?.id === property.id ? "bg-zinc-900" : "",
                  ].join(" ")}
                  onClick={() => {
                    setActiveProperty(property);
                    setSelectorOpen(false);
                  }}
                  type="button"
                >
                  <span className="block text-sm font-medium text-zinc-100">
                    {property.name}
                  </span>
                  <span className="mt-1 block text-xs text-zinc-500">
                    {property.domain}
                  </span>
                </button>
              ))}
            </div>

            <div className="border-t border-zinc-800 p-2">
              <Button
                className="w-full justify-start"
                onClick={() => {
                  setPropertyError("");
                  setAddDialogOpen(true);
                }}
                size="sm"
                variant="ghost"
              >
                <Plus className="h-4 w-4" />
                Add Property
              </Button>
              {propertyError && (
                <p className="mt-2 text-xs leading-5 text-red-300">
                  {propertyError}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
                Property
              </p>
              <DialogTitle>Add Property</DialogTitle>
              <DialogDescription>
                Add a tracked website. This Property becomes the active
                context after creation.
              </DialogDescription>
          </DialogHeader>

            <div className="mt-5 space-y-3">
              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">Property Name *</span>
                <input
                  className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
                  value={addForm.name}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">Brand Name *</span>
                <input
                  className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
                  value={addForm.brand_name}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      brand_name: event.target.value,
                    }))
                  }
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">Website URL *</span>
                <input
                  className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
                  placeholder="https://example.com"
                  value={addForm.domain}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      domain: event.target.value,
                    }))
                  }
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">
                  Description (optional)
                </span>
                <textarea
                  className="min-h-24 w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
                  value={addForm.description}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      description: event.target.value,
                    }))
                  }
                />
              </label>
            </div>

            {propertyError && (
              <p className="mt-3 text-sm text-red-300">{propertyError}</p>
            )}

            <DialogFooter className="mt-5">
              <Button
                onClick={() => setAddDialogOpen(false)}
                size="sm"
                variant="ghost"
              >
                Cancel
              </Button>
              <Button
                disabled={creatingProperty}
                onClick={handleAddProperty}
                size="sm"
              >
                {creatingProperty ? "Creating..." : "Create Property"}
              </Button>
            </DialogFooter>
        </DialogContent>
      </Dialog>

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
          <p className="mt-1 text-xs text-zinc-500">
            Changing property scopes dashboard data, history, and experiments.
          </p>
        </div>
      </div>
    </aside>
  );
}
