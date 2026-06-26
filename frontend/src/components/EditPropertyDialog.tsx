import { Loader2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import { Button } from "../../@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../@/components/ui/dialog";
import { Input } from "../../@/components/ui/input";
import { Label } from "../../@/components/ui/label";

import type { Property } from "@/api/properties";
import { useProperty } from "@/contexts/PropertyContext";

type EditPropertyDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  property: Property | null;
  onSaved: (property: Property) => void;
  onError: () => void;
};

export function EditPropertyDialog({
  onError,
  onOpenChange,
  onSaved,
  open,
  property,
}: EditPropertyDialogProps) {
  const { updateActiveProperty } = useProperty();
  const [form, setForm] = useState<{
    name?: string;
    domain?: string;
    description?: string;
  }>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [savingProperty, setSavingProperty] = useState(false);

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      setForm({});
      setFormErrors({});
    }

    onOpenChange(nextOpen);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!property || !validatePropertyForm()) {
      return;
    }

    try {
      setSavingProperty(true);
      const currentForm = getCurrentForm();
      const updatedProperty = await updateActiveProperty({
        name: currentForm.name.trim(),
        domain: currentForm.domain.trim(),
        brand_name: currentForm.name.trim(),
        description: currentForm.description.trim() || null,
      });

      if (!updatedProperty) {
        throw new Error("Property not found");
      }

      onOpenChange(false);
      onSaved(updatedProperty);
    } catch {
      onError();
    } finally {
      setSavingProperty(false);
    }
  }

  function validatePropertyForm() {
    const errors: Record<string, string> = {};
    const currentForm = getCurrentForm();

    if (!currentForm.name.trim()) {
      errors.name = "Property Name is required.";
    }

    if (!currentForm.domain.trim()) {
      errors.domain = "Domain is required.";
    } else if (!isValidDomainOrUrl(currentForm.domain.trim())) {
      errors.domain = "Enter a valid domain, for example example.com.";
    }

    setFormErrors(errors);

    return Object.keys(errors).length === 0;
  }

  function getCurrentForm() {
    return {
      name: form.name ?? property?.name ?? "",
      domain: form.domain ?? property?.domain ?? "",
      description: form.description ?? property?.description ?? "",
    };
  }

  const currentForm = getCurrentForm();

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">
            Property
          </p>
          <DialogTitle>Edit Property</DialogTitle>
          <DialogDescription>
            Update the active tracked website. Changes apply across the whole
            workspace.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="mt-5 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-property-name">Property Name *</Label>
              <Input
                id="edit-property-name"
                aria-invalid={Boolean(formErrors.name)}
                className="h-auto border-zinc-800 bg-black p-3"
                value={currentForm.name}
                onChange={(event) =>
                  setForm((current) => ({
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
              <Label htmlFor="edit-property-domain">Domain *</Label>
              <Input
                id="edit-property-domain"
                aria-invalid={Boolean(formErrors.domain)}
                className="h-auto border-zinc-800 bg-black p-3"
                placeholder="geoairesume-web-six.vercel.app"
                value={currentForm.domain}
                onChange={(event) =>
                  setForm((current) => ({
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
              <Label htmlFor="edit-property-description">
                Description (optional)
              </Label>
              <textarea
                id="edit-property-description"
                className="min-h-24 w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
                value={currentForm.description}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
              />
            </div>
          </div>

          <DialogFooter className="mt-5">
            <Button
              disabled={savingProperty}
              onClick={() => handleOpenChange(false)}
              size="sm"
              type="button"
              variant="ghost"
            >
              Cancel
            </Button>
            <Button disabled={savingProperty} size="sm" type="submit">
              {savingProperty && <Loader2 className="h-4 w-4 animate-spin" />}
              {savingProperty ? "Saving..." : "Save Property"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function isValidDomainOrUrl(value: string) {
  try {
    const candidate = value.includes("://") ? value : `https://${value}`;
    const url = new URL(candidate);

    return (
      (url.protocol === "http:" || url.protocol === "https:") &&
      Boolean(url.hostname.includes("."))
    );
  } catch {
    return false;
  }
}
