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

type CreatePropertyDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (property: Property) => void;
  onError: () => void;
};

export function CreatePropertyDialog({
  onCreated,
  onError,
  onOpenChange,
  open,
}: CreatePropertyDialogProps) {
  const { addProperty } = useProperty();
  const [form, setForm] = useState({
    name: "",
    brand_name: "",
    domain: "",
    description: "",
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [creatingProperty, setCreatingProperty] = useState(false);

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      setFormErrors({});
    }

    onOpenChange(nextOpen);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!validatePropertyForm()) {
      return;
    }

    try {
      setCreatingProperty(true);
      const createdProperty = await addProperty({
        name: form.name.trim(),
        domain: form.domain.trim(),
        brand_name: form.brand_name.trim(),
        description: form.description.trim() || null,
      });

      setForm({
        name: "",
        brand_name: "",
        domain: "",
        description: "",
      });
      setFormErrors({});
      onOpenChange(false);
      onCreated(createdProperty);
    } catch {
      onError();
    } finally {
      setCreatingProperty(false);
    }
  }

  function validatePropertyForm() {
    const errors: Record<string, string> = {};

    if (!form.name.trim()) {
      errors.name = "Property Name is required.";
    }

    if (!form.brand_name.trim()) {
      errors.brand_name = "Brand Name is required.";
    }

    if (!form.domain.trim()) {
      errors.domain = "Website URL is required.";
    } else if (!isValidWebsiteUrl(form.domain.trim())) {
      errors.domain = "Enter a valid URL, for example https://example.com.";
    }

    setFormErrors(errors);

    return Object.keys(errors).length === 0;
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
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

        <form onSubmit={handleSubmit}>
          <div className="mt-5 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="property-name">Property Name *</Label>
              <Input
                id="property-name"
                aria-invalid={Boolean(formErrors.name)}
                className="h-auto border-zinc-800 bg-black p-3"
                value={form.name}
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
              <Label htmlFor="property-brand">Brand Name *</Label>
              <Input
                id="property-brand"
                aria-invalid={Boolean(formErrors.brand_name)}
                className="h-auto border-zinc-800 bg-black p-3"
                value={form.brand_name}
                onChange={(event) =>
                  setForm((current) => ({
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
                value={form.domain}
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
              <Label htmlFor="property-description">
                Description (optional)
              </Label>
              <textarea
                id="property-description"
                className="min-h-24 w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
                value={form.description}
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
              disabled={creatingProperty}
              onClick={() => {
                handleOpenChange(false);
              }}
              size="sm"
              type="button"
              variant="ghost"
            >
              Cancel
            </Button>
            <Button disabled={creatingProperty} size="sm" type="submit">
              {creatingProperty && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              {creatingProperty ? "Creating..." : "Create Property"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
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
