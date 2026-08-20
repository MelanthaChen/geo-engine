import { useEffect, useState } from "react";

import {
  fetchProviderStatus,
  type ProviderStatus,
} from "@/api/providers";
import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import { useProperty } from "@/contexts/PropertyContext";
import { Page, PageHeader, ResponsiveGrid } from "@/components/layout/PageLayout";

const integrationSections = [
  {
    title: "Publishing Accounts",
    note: "TODO: connect account management once backend account CRUD endpoints are available.",
  },
  {
    title: "Google Search Console",
    note: "TODO: connect GSC configuration once backend integration endpoints are available.",
  },
  {
    title: "Reddit Session",
    note: "TODO: connect local session status once publisher-agent health endpoints are available.",
  },
];

export function Settings() {
  const { activeProperty, updateActiveProperty } = useProperty();
  const [form, setForm] = useState({
    name: "",
    brand_name: "",
    domain: "",
    description: "",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [llmProviders, setLlmProviders] = useState<ProviderStatus[]>([]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setForm({
        name: activeProperty?.name || "",
        brand_name: activeProperty?.brand_name || "",
        domain: activeProperty?.domain || "",
        description: activeProperty?.description || "",
      });
      setMessage("");
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [activeProperty]);

  useEffect(() => {
    let isMounted = true;

    async function loadProviderStatus() {
      try {
        const providers = await fetchProviderStatus();

        if (isMounted) {
          setLlmProviders(providers);
        }
      } catch (error) {
        console.error(error);
        if (isMounted) {
          setLlmProviders([]);
        }
      }
    }

    void loadProviderStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleSave() {
    if (!activeProperty) {
      return;
    }

    try {
      setSaving(true);
      setMessage("");
      await updateActiveProperty({
        name: form.name,
        brand_name: form.brand_name || form.name,
        domain: form.domain,
        description: form.description || null,
      });
      setMessage("Property settings saved.");
    } catch (error) {
      console.error(error);
      setMessage("Failed to save property settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Admin"
        title="Settings"
        description="Edit the active Property and review integration configuration gaps."
        meta={activeProperty && (
          <p>
            Current Property:{" "}
            <span className="text-zinc-100">{activeProperty.name}</span>
            {" • "}
            Domain:{" "}
            <span className="text-zinc-100">{activeProperty.domain}</span>
          </p>
        )}
      />

      <ResponsiveGrid minItemWidth={460}>
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="space-y-4 p-6">
            <div>
              <h2 className="text-lg font-semibold text-zinc-50">
                Backend Configuration
              </h2>
              <p className="mt-1 text-sm text-zinc-500">
                Current Property is the authoritative website context.
              </p>
            </div>

            <div className="space-y-3">
              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">Property Name</span>
                <input
                  className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition placeholder:text-zinc-700 focus:border-blue-500"
                  value={form.name}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      name: event.target.value,
                    }))
                  }
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">Brand Name</span>
                <input
                  className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition placeholder:text-zinc-700 focus:border-blue-500"
                  value={form.brand_name}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      brand_name: event.target.value,
                    }))
                  }
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">Domain</span>
                <input
                  className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition placeholder:text-zinc-700 focus:border-blue-500"
                  value={form.domain}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      domain: event.target.value,
                    }))
                  }
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-zinc-400">Description</span>
                <textarea
                  className="min-h-28 w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition placeholder:text-zinc-700 focus:border-blue-500"
                  value={form.description}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      description: event.target.value,
                    }))
                  }
                />
              </label>
            </div>

            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-zinc-500">{message}</p>
              <Button
                disabled={!activeProperty || saving}
                onClick={handleSave}
              >
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {integrationSections.map((section) => (
          <Card key={section.title} className="border-zinc-800 bg-zinc-950">
            <CardContent className="space-y-4 p-6">
              <div>
                <h2 className="text-lg font-semibold text-zinc-50">
                  {section.title}
                </h2>
                <p className="mt-1 text-sm text-zinc-500">{section.note}</p>
              </div>
            </CardContent>
          </Card>
        ))}

        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="space-y-4 p-6">
            <div>
              <h2 className="text-lg font-semibold text-zinc-50">
                LLM Providers
              </h2>
              <p className="mt-1 text-sm text-zinc-500">
                Provider registry status for GEO generation and citation
                testing.
              </p>
            </div>

            <div className="space-y-3">
              {llmProviders.map((provider) => (
                <div
                  key={provider.name}
                  className="flex items-center justify-between gap-4 rounded-lg border border-zinc-800 bg-black p-4"
                >
                  <div>
                    <p className="text-sm font-medium text-zinc-100">
                      {provider.name}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {provider.detail}
                    </p>
                  </div>
                  <span
                    className={
                      provider.status === "connected"
                        ? "rounded-full border border-emerald-700 bg-emerald-950 px-3 py-1 text-xs font-medium text-emerald-300"
                        : "rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-400"
                    }
                  >
                    {formatProviderStatus(provider.status)}
                  </span>
                </div>
              ))}

              {llmProviders.length === 0 && (
                <p className="text-sm text-zinc-500">
                  Provider status is unavailable.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </ResponsiveGrid>
    </Page>
  );
}

function formatProviderStatus(status: ProviderStatus["status"]) {
  if (status === "connected") {
    return "Connected";
  }

  if (status === "missing_session") {
    return "Session Required";
  }

  return "Coming Soon";
}
