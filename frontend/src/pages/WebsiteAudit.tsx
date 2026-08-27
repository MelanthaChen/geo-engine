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
import {
  EmptyState,
  Page,
  PageHeader,
  SectionHeader,
  SummaryCard,
  SummaryGrid,
} from "@/components/layout/PageLayout";

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
    <Page>
      <PageHeader
        eyebrow="Analysis"
        title="Website Audit"
        description="Analyze the active Property for GEO readiness, missing topics, and future citation opportunities."
        meta={activeProperty && (
          <p>
            Current Property:{" "}
            <span className="text-zinc-100">{activeProperty.name}</span>
            {" • "}
            Website URL:{" "}
            <span className="text-zinc-100">{activeProperty.domain}</span>
          </p>
        )}
      />

      <SummaryGrid>
        <SummaryCard
          label="GEO Score"
          value={audit?.overall_geo_score == null ? "Not recorded" : `${audit.overall_geo_score}/100`}
          detail="Overall audit result"
        />
        <SummaryCard
          label="Pages Crawled"
          value={String(audit?.pages?.length || 0)}
          detail="Stored in the latest audit"
        />
        <SummaryCard
          label="Missing Topics"
          value={String(audit?.missing_geo_topics?.length || 0)}
          detail="GEO content opportunities"
        />
        <SummaryCard
          label="Last Audit"
          value={audit?.last_audit ? new Date(audit.last_audit).toLocaleDateString() : "Not recorded"}
          detail={audit?.last_audit ? new Date(audit.last_audit).toLocaleTimeString() : "Run an audit to establish a baseline"}
        />
      </SummaryGrid>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="flex flex-col gap-5 p-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-zinc-50">Audit controls</h2>
            <p className="mt-1 text-sm leading-6 text-zinc-500">
              Analyze the selected property and replace the current stored audit result.
            </p>
            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
              <span className="text-zinc-500">Property <strong className="ml-1 font-medium text-zinc-200">{activeProperty?.name || "Not selected"}</strong></span>
              <span className="text-zinc-500">Website <strong className="ml-1 font-medium text-zinc-200">{activeProperty?.domain || "Not selected"}</strong></span>
            </div>
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

      <section>
        <SectionHeader
          title="Audit findings"
          description="Score components, content gaps, and structural recommendations from the latest stored audit."
        />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
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
      </section>

      <section>
        <SectionHeader
          title="Crawled pages"
          description="Page-level evidence retained by the latest website audit."
        />
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-6">
          <div className="mt-4 space-y-2">
            {(audit?.pages || []).map((page) => (
              <PageAuditRow key={page.id} page={page} />
            ))}
            {(!audit?.pages || audit.pages.length === 0) && (
              <EmptyState>No crawled pages are stored yet. Run an audit to populate page-level evidence.</EmptyState>
            )}
          </div>
          </CardContent>
        </Card>
      </section>
    </Page>
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
            <EmptyState className="min-h-24">{emptyText}</EmptyState>
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
