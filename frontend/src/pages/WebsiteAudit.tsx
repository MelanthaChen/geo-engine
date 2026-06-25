import { useState } from "react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import { runWebsiteAudit, type AuditResult } from "@/api/audit";
import { useProperty } from "@/contexts/PropertyContext";

type AuditCardProps = {
  title: string;
  items: string[];
  emptyText: string;
};

export function WebsiteAudit() {
  const { activeProperty, activePropertyId } = useProperty();
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function handleAnalyzeWebsite() {
    if (!activePropertyId) {
      setMessage("Select a Property before running an audit.");
      return;
    }

    try {
      setLoading(true);
      setMessage("");
      const result = await runWebsiteAudit(activePropertyId);

      setAudit(result);
    } catch (error) {
      console.error(error);
      setMessage("Website audit failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Analysis
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Website Audit
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Analyze the active Property for GEO readiness, missing topics, and
          future citation opportunities.
        </p>
        {activeProperty && (
          <p className="mt-3 text-sm text-zinc-400">
            Current Property:{" "}
            <span className="text-zinc-100">{activeProperty.name}</span>
            {" • "}
            Website URL:{" "}
            <span className="text-zinc-100">{activeProperty.domain}</span>
          </p>
        )}
      </div>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="flex flex-col gap-5 p-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="grid gap-4 md:grid-cols-3">
            <AuditFact
              label="Current Property"
              value={activeProperty?.name || "No property selected"}
            />
            <AuditFact
              label="Website URL"
              value={activeProperty?.domain || "No website selected"}
            />
            <AuditFact
              label="Last Audit"
              value={
                audit?.last_audit
                  ? new Date(audit.last_audit).toLocaleString()
                  : "No data yet."
              }
            />
          </div>

          <Button
            disabled={!activePropertyId || loading}
            onClick={handleAnalyzeWebsite}
          >
            {loading ? "Analyzing..." : "Analyze Website"}
          </Button>
        </CardContent>
      </Card>

      {message && (
        <div className="rounded-lg border border-amber-800 bg-amber-950/50 px-5 py-4 text-sm text-amber-200">
          {message}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-6">
            <p className="text-sm text-zinc-500">Overall GEO Score</p>
            <p className="mt-3 text-3xl font-semibold text-zinc-50">
              {audit?.overall_geo_score ?? "No data yet."}
            </p>
          </CardContent>
        </Card>

        <AuditCard
          title="Brand Understanding"
          items={audit?.brand_understanding.items || []}
          emptyText="No brand understanding audit yet."
        />
        <AuditCard
          title="Missing Pages"
          items={audit?.missing_pages || []}
          emptyText="No missing pages detected yet."
        />
        <AuditCard
          title="Missing GEO Topics"
          items={audit?.missing_geo_topics || []}
          emptyText="No missing GEO topics detected yet."
        />
        <AuditCard
          title="Internal Linking Suggestions"
          items={audit?.internal_linking_suggestions || []}
          emptyText="No internal linking suggestions yet."
        />
        <AuditCard
          title="FAQ Opportunities"
          items={audit?.faq_opportunities || []}
          emptyText="No FAQ opportunities yet."
        />
        <AuditCard
          title="Content Recommendations"
          items={audit?.content_recommendations || []}
          emptyText="No content recommendations yet."
        />
      </div>
    </div>
  );
}

function AuditFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-48 rounded-lg border border-zinc-800 bg-black p-4">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-zinc-100">{value}</p>
    </div>
  );
}

function AuditCard({ title, items, emptyText }: AuditCardProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <h2 className="text-lg font-semibold text-zinc-50">{title}</h2>
        <div className="mt-4 space-y-2">
          {items.map((item) => (
            <div
              key={item}
              className="rounded-lg border border-zinc-800 bg-black p-3 text-sm text-zinc-300"
            >
              {item}
            </div>
          ))}
          {items.length === 0 && (
            <p className="text-sm text-zinc-500">{emptyText}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
