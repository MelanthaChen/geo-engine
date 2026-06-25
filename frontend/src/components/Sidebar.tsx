import {
  Check,
  ChevronDown,
  FileSearch,
  FlaskConical,
  History,
  LayoutDashboard,
  Loader2,
  Plus,
  PenLine,
  Send,
  Settings,
} from "lucide-react";
import { type FormEvent, useState } from "react";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../@/components/ui/dropdown-menu";
import { Input } from "../../@/components/ui/input";
import { Label } from "../../@/components/ui/label";
import { Separator } from "../../@/components/ui/separator";

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
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [creatingProperty, setCreatingProperty] = useState(false);
  const [toast, setToast] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  function showToast(type: "success" | "error", message: string) {
    setToast({ type, message });
    window.setTimeout(() => setToast(null), 3200);
  }

  function validatePropertyForm() {
    const errors: Record<string, string> = {};

    if (!addForm.name.trim()) {
      errors.name = "Property Name is required.";
    }

    if (!addForm.brand_name.trim()) {
      errors.brand_name = "Brand Name is required.";
    }

    if (!addForm.domain.trim()) {
      errors.domain = "Website URL is required.";
    } else if (!isValidWebsiteUrl(addForm.domain.trim())) {
      errors.domain = "Enter a valid URL, for example https://example.com.";
    }

    setFormErrors(errors);

    return Object.keys(errors).length === 0;
  }

  async function handleAddProperty(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!validatePropertyForm()) {
      return;
    }

    try {
      setCreatingProperty(true);
      const createdProperty = await addProperty({
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
      setFormErrors({});
      setAddDialogOpen(false);
      setSelectorOpen(false);
      showToast("success", `${createdProperty.name} created.`);
    } catch (error) {
      console.error(error);
      showToast("error", "Failed to create property.");
    } finally {
      setCreatingProperty(false);
    }
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-zinc-800 bg-zinc-950">
      {toast && (
        <div
          className={[
            "fixed right-6 top-6 z-[70] rounded-xl border px-4 py-3 text-sm shadow-xl",
            toast.type === "success"
              ? "border-emerald-700 bg-emerald-950 text-emerald-100"
              : "border-red-700 bg-red-950 text-red-100",
          ].join(" ")}
        >
          {toast.message}
        </div>
      )}

      <div className="border-b border-zinc-800 p-4">
        <DropdownMenu open={selectorOpen} onOpenChange={setSelectorOpen}>
          <DropdownMenuTrigger asChild>
            <button
              className="flex w-full items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-3 text-left shadow-sm transition hover:border-zinc-700 hover:bg-zinc-900/80 data-[state=open]:border-zinc-700"
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
          </DropdownMenuTrigger>

          <DropdownMenuContent align="start" className="w-64">
            <DropdownMenuLabel>Properties</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <div className="max-h-72 overflow-y-auto py-1">
              {properties.map((property) => {
                const isCurrent = activeProperty?.id === property.id;

                return (
                  <DropdownMenuItem
                    key={property.id}
                    className={[
                      "items-start gap-3",
                      isCurrent ? "bg-zinc-900" : "",
                    ].join(" ")}
                    onSelect={() => {
                      setActiveProperty(property);
                      setSelectorOpen(false);
                    }}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-zinc-100">
                        {property.name}
                      </p>
                      <p className="mt-1 truncate text-xs text-zinc-500">
                        {property.domain}
                      </p>
                      {isCurrent && (
                        <p className="mt-1 text-xs font-medium text-blue-300">
                          Current
                        </p>
                      )}
                    </div>
                    {isCurrent && (
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-blue-300" />
                    )}
                  </DropdownMenuItem>
                );
              })}
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="font-medium text-zinc-100"
              onSelect={(event) => {
                event.preventDefault();
                setFormErrors({});
                setSelectorOpen(false);
                setAddDialogOpen(true);
              }}
            >
              <Plus className="h-4 w-4" />
              Add Property
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
              Property
            </p>
            <DialogTitle>Create Property</DialogTitle>
            <DialogDescription>
              Add a tracked website. This Property becomes the active context
              after creation.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleAddProperty}>
            <div className="mt-5 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="property-name">Property Name *</Label>
                <Input
                  id="property-name"
                  aria-invalid={Boolean(formErrors.name)}
                  className="h-auto border-zinc-800 bg-black p-3"
                  value={addForm.name}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                />
                {formErrors.name && (
                  <p className="text-xs text-red-300">{formErrors.name}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="property-brand">Brand Name *</Label>
                <Input
                  id="property-brand"
                  aria-invalid={Boolean(formErrors.brand_name)}
                  className="h-auto border-zinc-800 bg-black p-3"
                  value={addForm.brand_name}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      brand_name: event.target.value,
                    }))
                  }
                />
                {formErrors.brand_name && (
                  <p className="text-xs text-red-300">
                    {formErrors.brand_name}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="property-url">Website URL *</Label>
                <Input
                  id="property-url"
                  aria-invalid={Boolean(formErrors.domain)}
                  className="h-auto border-zinc-800 bg-black p-3"
                  placeholder="https://example.com"
                  value={addForm.domain}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      domain: event.target.value,
                    }))
                  }
                />
                {formErrors.domain && (
                  <p className="text-xs text-red-300">{formErrors.domain}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="property-description">
                  Description (optional)
                </Label>
                <textarea
                  id="property-description"
                  className="min-h-24 w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
                  value={addForm.description}
                  onChange={(event) =>
                    setAddForm((current) => ({
                      ...current,
                      description: event.target.value,
                    }))
                  }
                />
              </div>
            </div>

            <DialogFooter className="mt-5">
              <Button
                disabled={creatingProperty}
                onClick={() => setAddDialogOpen(false)}
                size="sm"
                type="button"
                variant="ghost"
              >
                Cancel
              </Button>
              <Button
                disabled={creatingProperty}
                size="sm"
                type="submit"
              >
                {creatingProperty && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                {creatingProperty ? "Creating..." : "Create Property"}
              </Button>
            </DialogFooter>
          </form>
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
          <Separator className="my-3" />
          <p className="mt-1 text-xs text-zinc-500">
            Changing property scopes dashboard data, history, and experiments.
          </p>
        </div>
      </div>
    </aside>
  );
}

function isValidWebsiteUrl(value: string) {
  try {
    const url = new URL(value);

    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}
