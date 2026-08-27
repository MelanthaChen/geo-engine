import { Check, ChevronDown, Pencil, Plus, RefreshCw } from "lucide-react";
import { type MouseEvent, useRef, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../@/components/ui/dropdown-menu";

import { CreatePropertyDialog } from "@/components/CreatePropertyDialog";
import { EditPropertyDialog } from "@/components/EditPropertyDialog";
import type { Property } from "@/api/properties";
import { useProperty } from "@/contexts/PropertyContext";

type QueuedDialog = "create" | "edit";

export function PropertySelector() {
  const {
    activeProperty,
    loading,
    properties,
    refreshProperties,
    setActiveProperty,
  } = useProperty();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const queuedDialogRef = useRef<QueuedDialog | null>(null);
  const [toast, setToast] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  function showToast(type: "success" | "error", message: string) {
    setToast({ type, message });
    window.setTimeout(() => setToast(null), 3200);
  }

  function openQueuedDialog() {
    const queuedDialog = queuedDialogRef.current;

    if (!queuedDialog) {
      return;
    }

    queuedDialogRef.current = null;

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        if (queuedDialog === "create") {
          setCreateDialogOpen(true);
        }

        if (queuedDialog === "edit") {
          setEditDialogOpen(true);
        }
      });
    });
  }

  function queueDialog(dialog: QueuedDialog) {
    queuedDialogRef.current = dialog;
    setDropdownOpen(false);
    openQueuedDialog();
  }

  function handleDialogMenuItem(
    event: { preventDefault: () => void },
    dialog: QueuedDialog,
  ) {
    event.preventDefault();
    queueDialog(dialog);
  }

  function handleDialogMenuItemClick(
    event: MouseEvent<HTMLDivElement>,
    dialog: QueuedDialog,
  ) {
    if (event.currentTarget.getAttribute("data-disabled") !== null) {
      return;
    }

    handleDialogMenuItem(event, dialog);
  }

  function handleDropdownOpenChange(nextOpen: boolean) {
    setDropdownOpen(nextOpen);

    if (!nextOpen) {
      openQueuedDialog();
    }
  }

  function handleCreated(property: Property) {
    showToast("success", `${property.name} created.`);
  }

  function handleSaved(property: Property) {
    showToast("success", `${property.name} saved.`);
  }

  async function handleRefreshProperties() {
    try {
      await refreshProperties();
      showToast("success", "Properties refreshed.");
    } catch {
      showToast("error", "Failed to refresh properties.");
    }
  }

  return (
    <>
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

      <DropdownMenu
        modal={false}
        open={dropdownOpen}
        onOpenChange={handleDropdownOpenChange}
      >
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
                    setDropdownOpen(false);
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
            className="gap-2 font-medium text-zinc-100"
            onSelect={(event) => {
              handleDialogMenuItem(event, "create");
            }}
            onClick={(event) => {
              handleDialogMenuItemClick(event, "create");
            }}
          >
            <Plus className="h-4 w-4" />
            Add Property
          </DropdownMenuItem>
          <DropdownMenuItem
            className="gap-2 font-medium text-zinc-100"
            disabled={!activeProperty}
            onSelect={(event) => {
              handleDialogMenuItem(event, "edit");
            }}
            onClick={(event) => {
              handleDialogMenuItemClick(event, "edit");
            }}
          >
            <Pencil className="h-4 w-4" />
            Edit Current Property
          </DropdownMenuItem>
          <DropdownMenuItem
            className="gap-2 font-medium text-zinc-100"
            onSelect={(event) => {
              event.preventDefault();
              setDropdownOpen(false);
              void handleRefreshProperties();
            }}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh Properties
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CreatePropertyDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={handleCreated}
        onError={() => showToast("error", "Failed to create property.")}
      />
      <EditPropertyDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        property={activeProperty}
        onSaved={handleSaved}
        onError={() => showToast("error", "Failed to save property.")}
      />
    </>
  );
}
