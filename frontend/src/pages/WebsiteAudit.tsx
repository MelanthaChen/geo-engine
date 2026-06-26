import { useEffect, useState } from "react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import {
  fetchLatestWebsiteAudit,
  runWebsiteAudit,
  type AuditResult,
  type WebsitePageAudit,
} from "@/api/audit";
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

  useEffect(() => {
    let isMounted = true;

    async function loadLatestAudit() {
      if (!activePropertyId) {
        setAudit(null);
        return;
      }

      try {
        const result = await fetchLatestWebsiteAudit(activePropertyId);

        if (isMounted) {
          setAudit(result);
        }
      } catch (error) {
        console.error(error);
      }
    }

    void loadLatestAudit();

    return () => {
      isMounted = false;
    };
  }, [activePropertyId]);

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
              {audit?.overall_geo_score === null ||
              audit?.overall_geo_score === undefined
                ? "No data yet."
                : `${audit.overall_geo_score}/100`}
            </p>
          </CardContent>
        </Card>

        <AuditCard
          title="Score Components"
          items={formatSubscores(audit)}
          emptyText="No component scores yet."
        />

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

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-zinc-50">Crawled Pages</h2>
          <div className="mt-4 space-y-2">
            {(audit?.pages || []).map((page) => (
              <PageAuditRow key={page.id} page={page} />
            ))}
            {(!audit?.pages || audit.pages.length === 0) && (
              <p className="text-sm text-zinc-500">
                No crawled pages stored yet.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
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

function PageAuditRow({ page }: { page: WebsitePageAudit }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <p className="truncate text-sm font-medium text-zinc-100">{page.url}</p>
      <p className="mt-1 text-sm text-zinc-400">
        {page.page_title || page.h1 || "Untitled page"}
      </p>
      <p className="mt-2 text-xs text-zinc-500">
        Status: {page.status_code || "N/A"} • Words: {page.word_count} •
        Internal links: {page.internal_link_count}
      </p>
    </div>
  );
}

function formatSubscores(audit: AuditResult | null) {
  if (!audit?.subscores) {
    return [];
  }

  return [
    `Content Coverage: ${formatScore(audit.subscores.content_coverage)}`,
    `FAQ Coverage: ${formatScore(audit.subscores.faq_coverage)}`,
    `Internal Linking: ${formatScore(audit.subscores.internal_linking)}`,
    `Website Structure: ${formatScore(audit.subscores.website_structure)}`,
    `Brand Clarity: ${formatScore(audit.subscores.brand_clarity)}`,
    `Trust Signals: ${formatScore(audit.subscores.trust_signals)}`,
  ];
}

function formatScore(score?: number | null) {
  return score === null || score === undefined ? "No data" : `${score}/100`;
}
