import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, ChevronDown, CircleDashed, ExternalLink, FileSearch } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";
import {
  fetchLatestWebsiteAudit,
  runWebsiteAudit,
  type AuditFinding,
  type AuditResult,
  type OptimizationOpportunity,
  type WebsiteFeature,
  type WebsitePageAudit,
} from "@/api/audit";
import { EmptyState, Page, PageHeader, SectionHeader, SummaryCard, SummaryGrid } from "@/components/layout/PageLayout";
import { useProperty } from "@/contexts/PropertyContext";

export function WebsiteAudit() {
  const navigate = useNavigate();
  const { activeProperty, activePropertyId } = useProperty();
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [previousAudit, setPreviousAudit] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let isMounted = true;
    async function loadLatestAudit() {
      setAudit(null);
      setPreviousAudit(null);
      setMessage("");
      if (!activePropertyId) {
        return;
      }
      try {
        const result = await fetchLatestWebsiteAudit(activePropertyId);
        if (isMounted) setPreviousAudit(result);
      } catch (error) {
        console.error(error);
      }
    }
    void loadLatestAudit();
    return () => { isMounted = false; };
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

  const features = Object.entries(audit?.website_features || {});
  const opportunities = audit?.optimization_opportunities || [];

  function continueToOptimization() {
    if (!audit) return;
    navigate(`/predictor?website_id=${audit.property_id}&audit_id=${audit.id}`, {
      state: {
        audit: {
          website_id: audit.property_id,
          audit_id: audit.id,
          property_name: audit.property_name,
          website_url: audit.website_url,
          website_features: audit.website_features || {},
          optimization_opportunities: audit.optimization_opportunities || [],
        },
      },
    });
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Objective analysis"
        title="Website Audit"
        description="Inspect measurable website characteristics and source evidence. Audit findings describe the current website; they are not predictions or validated optimization advice."
        meta={activeProperty && <p>Current Property: <span className="text-zinc-100">{activeProperty.name}</span>{" • "}Website URL: <span className="text-zinc-100">{activeProperty.domain}</span></p>}
      />

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="flex flex-col gap-5 p-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-start gap-4">
            <div className="rounded-lg border border-zinc-800 bg-black p-3 text-zinc-300"><FileSearch className="h-5 w-5" /></div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-50">{audit ? "Analyze current website again" : `Ready to analyze ${activeProperty?.name || "the selected website"}`}</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">{audit ? "Run another live crawl to create a new stored audit result." : "No audit has been run in this session. Start a live crawl to measure structure, content, links, and coverage."}</p>
              <p className="mt-2 text-xs text-zinc-600">No predicted gains, PAWC estimates, or visibility estimates are produced.</p>
            </div>
          </div>
          <Button disabled={!activePropertyId || loading} onClick={handleAnalyzeWebsite}>{loading ? "Analyzing…" : "Analyze Website"}</Button>
        </CardContent>
      </Card>

      {message && <div className="rounded-lg border border-amber-800 bg-amber-950/50 px-5 py-4 text-sm text-amber-200">{message}</div>}

      {loading && <div className="rounded-lg border border-blue-900 bg-blue-950/30 px-5 py-4 text-sm text-blue-200">Live website crawl in progress. A new audit record will be created when analysis completes.</div>}

      {audit?.status === "completed" && <Card className="border-blue-900 bg-blue-950/20">
        <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="text-lg font-semibold text-zinc-50">Current audit complete</h2><p className="mt-1 text-sm text-zinc-400">Website #{audit.property_id}, audit #{audit.id}, {features.length} features, and {opportunities.length} opportunities from this live run are ready for the optimization step.</p></div>
          <Button onClick={continueToOptimization}>Continue to Optimization</Button>
        </CardContent>
      </Card>}

      {audit && <AuditResults audit={audit} />}

      {previousAudit && <details className="group rounded-xl border border-zinc-800 bg-zinc-950">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 p-5 [&::-webkit-details-marker]:hidden">
          <div><h2 className="text-lg font-semibold text-zinc-50">Previous audits</h2><p className="mt-1 text-sm text-zinc-500">Stored history is available for reference and is never treated as the current demo run.</p></div>
          <ChevronDown className="h-5 w-5 shrink-0 text-zinc-500 transition-transform group-open:rotate-180" />
        </summary>
        <div className="space-y-8 border-t border-zinc-800 p-5">
          <div className="rounded-lg border border-zinc-800 bg-black px-4 py-3"><p className="text-sm font-medium text-zinc-200">Audit #{previousAudit.id}</p><p className="mt-1 text-xs text-zinc-500">Completed {new Date(previousAudit.last_audit).toLocaleString()}. Historical results cannot continue to Optimization.</p></div>
          <AuditResults audit={previousAudit} />
        </div>
      </details>}
    </Page>
  );
}

function AuditResults({ audit }: { audit: AuditResult }) {
  const profile = audit.website_profile;
  const coverage = audit.crawl_coverage;
  const features = Object.entries(audit.website_features || {});
  const opportunities = audit.optimization_opportunities || [];

  return <>
      <section>
        <SectionHeader title="Website Overview" description="High-level scores already produced by the current audit methodology. Unmeasured dimensions remain explicitly unavailable." />
        <SummaryGrid className="xl:grid-cols-5">
          <SummaryCard label="Website Health" value={formatScore(profile?.website_health_score ?? audit.overall_geo_score)} detail="Existing overall audit score" />
          <SummaryCard label="Content Quality" value={formatScore(profile?.content_quality_score ?? audit.subscores?.content_coverage)} detail="Existing content coverage score" />
          <SummaryCard label="Technical Quality" value={formatScore(profile?.technical_quality_score ?? audit.subscores?.website_structure)} detail="Existing structure score" />
          <SummaryCard label="Authority" value={formatScore(profile?.authority_score ?? audit.subscores?.trust_signals)} detail="Existing trust signals score" />
          <SummaryCard label="Readability" value={formatScore(profile?.readability_score)} detail="Not measured by this audit" />
        </SummaryGrid>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <EvidenceMetric label="URLs discovered" value={coverage?.discovered_urls ?? audit.pages?.length ?? 0} />
          <EvidenceMetric label="URLs requested" value={coverage?.requested_urls ?? profile?.pages_crawled ?? audit.pages?.length ?? 0} />
          <EvidenceMetric label="Successful responses" value={coverage?.successful_responses ?? countSuccessfulPages(audit)} />
          <EvidenceMetric label="Unique analyzed pages" value={coverage?.unique_content_pages ?? profile?.successful_pages ?? countUniquePages(audit)} />
          <EvidenceMetric label="Duplicate/fallback responses" value={coverage?.duplicate_fallback_responses ?? countDuplicatePages(audit)} />
          <EvidenceMetric label="Skipped due to limit" value={coverage?.skipped_due_to_limit ?? 0} />
          <EvidenceMetric label="Total words" value={profile?.total_word_count ?? totalWords(audit)} />
          <EvidenceMetric label="Last analyzed" value={audit.last_audit ? new Date(audit.last_audit).toLocaleString() : "Not recorded"} />
        </div>
        {coverage && <div className={`mt-3 rounded-lg border px-4 py-3 text-sm ${coverage.truncated ? "border-amber-900 bg-amber-950/30 text-amber-200" : "border-emerald-900 bg-emerald-950/30 text-emerald-200"}`}>{coverage.truncated ? `Capped crawl: ${coverage.skipped_due_to_limit} discovered URLs were not requested because the configured limit is ${coverage.crawl_limit}.` : `Complete discovered inventory: all ${coverage.discovered_urls} URLs were requested using ${coverage.inventory_source === "sitemap" ? "the site sitemap" : "recursive internal-link discovery"}.`}</div>}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <FindingPanel title="Strengths" description="Positive characteristics directly supported by crawled evidence." findings={audit.strengths || []} tone="positive" emptyText="No objective strengths are available yet." />
        <FindingPanel title="Weaknesses" description="Observed gaps or missing evidence; no impact is implied." findings={audit.weaknesses || []} tone="negative" emptyText="No objective weaknesses are available yet." />
      </section>

      <section>
        <SectionHeader title="Website Features" description="Structured characteristics suitable for downstream analysis. Values come from existing audit measurements; unsupported features are marked unavailable." />
        {features.length ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{features.map(([key, feature]) => <FeatureCard key={key} feature={feature} />)}</div>
        ) : <EmptyState>Run a new audit to populate the structured website feature profile.</EmptyState>}
      </section>

      <section>
        <SectionHeader title="Optimization Opportunities" description="Candidate directions derived from audit findings. These opportunities are not validated improvements and contain no predicted gain." />
        <div className="space-y-3">
          {opportunities.map((opportunity) => <OpportunityRow key={opportunity.id} opportunity={opportunity} />)}
          {!opportunities.length && <EmptyState>No candidate optimization directions are available for this audit.</EmptyState>}
        </div>
      </section>

      <section>
        <SectionHeader title="Crawled Page Evidence" description="Page-level observations retained by the latest audit." />
        <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-6"><div className="space-y-2">
          {(audit.pages || []).map((page) => <PageAuditRow key={page.id} page={page} />)}
          {(!audit.pages || !audit.pages.length) && <EmptyState>No crawled pages are stored yet. Run an audit to populate page-level evidence.</EmptyState>}
        </div></CardContent></Card>
      </section>
    </>;
}

function FindingPanel({ title, description, findings, tone, emptyText }: { title: string; description: string; findings: AuditFinding[]; tone: "positive" | "negative"; emptyText: string }) {
  const Icon = tone === "positive" ? CheckCircle2 : AlertCircle;
  return <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-6">
    <h2 className="text-lg font-semibold text-zinc-50">{title}</h2><p className="mt-1 text-sm leading-6 text-zinc-500">{description}</p>
    <div className="mt-5 space-y-3">{findings.map((finding) => <div key={`${finding.feature_key}-${finding.label}`} className="flex gap-3 rounded-lg border border-zinc-800 bg-black p-4">
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${tone === "positive" ? "text-emerald-400" : "text-amber-400"}`} />
      <div><p className="text-sm font-medium text-zinc-100">{finding.label}</p><p className="mt-1 text-xs leading-5 text-zinc-500">{finding.evidence}</p></div>
    </div>)}{!findings.length && <EmptyState className="min-h-24">{emptyText}</EmptyState>}</div>
  </CardContent></Card>;
}

function FeatureCard({ feature }: { feature: WebsiteFeature }) {
  const available = feature.availability === "available";
  return <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-5">
    <div className="flex items-start justify-between gap-3"><p className="text-sm font-medium text-zinc-200">{feature.label}</p><span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${available ? "border-emerald-900 bg-emerald-950/50 text-emerald-400" : "border-zinc-800 bg-zinc-900 text-zinc-500"}`}>{feature.availability}</span></div>
    <p className={`mt-4 text-2xl font-semibold ${available ? "text-zinc-50" : "text-zinc-600"}`}>{available ? `${feature.value ?? "No data"}${feature.unit === "score" && typeof feature.value === "number" ? "/100" : ""}` : "Unavailable"}</p>
    {available && feature.unit && feature.unit !== "score" && <p className="mt-1 text-xs text-zinc-500">{feature.unit}</p>}
    <p className="mt-3 text-xs leading-5 text-zinc-500">{feature.evidence}</p>
  </CardContent></Card>;
}

function OpportunityRow({ opportunity }: { opportunity: OptimizationOpportunity }) {
  return <details className="group rounded-xl border border-zinc-800 bg-zinc-950 open:border-zinc-700">
    <summary className="flex cursor-pointer list-none items-center gap-4 p-5 [&::-webkit-details-marker]:hidden">
      <div className="rounded-lg border border-zinc-800 bg-black p-2 text-zinc-400"><CircleDashed className="h-4 w-4" /></div>
      <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold text-zinc-100">{opportunity.title}</h3><Tag>{formatCategory(opportunity.category)}</Tag><Tag>Not validated</Tag></div><p className="mt-1 truncate text-sm text-zinc-500">{opportunity.direction}</p></div>
      <ChevronDown className="h-4 w-4 shrink-0 text-zinc-500 transition-transform group-open:rotate-180" />
    </summary>
    <div className="border-t border-zinc-800 px-5 py-5"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">Evidence</p><p className="mt-2 text-sm leading-6 text-zinc-300">{opportunity.evidence}</p>
      {opportunity.evidence_url && <a className="mt-3 inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300" href={opportunity.evidence_url} target="_blank" rel="noreferrer">View observed page <ExternalLink className="h-3 w-3" /></a>}
      <div className="mt-4 rounded-lg border border-zinc-800 bg-black/60 px-4 py-3 text-xs leading-5 text-zinc-500">Generated from objective audit findings, not from a prediction model. No impact or visibility gain has been estimated.</div>
    </div>
  </details>;
}

function Tag({ children }: { children: string }) { return <span className="rounded-full border border-zinc-800 px-2 py-0.5 text-[10px] uppercase tracking-wide text-zinc-500">{children}</span>; }
function EvidenceMetric({ label, value }: { label: string; value: string | number }) { return <div className="rounded-lg border border-zinc-800 bg-zinc-950 px-4 py-3"><p className="text-xs text-zinc-500">{label}</p><p className="mt-1 truncate text-sm font-medium text-zinc-200">{value}</p></div>; }
function PageAuditRow({ page }: { page: WebsitePageAudit }) { return <div className={`rounded-lg border bg-black p-4 ${page.is_duplicate ? "border-amber-950/80 opacity-75" : "border-zinc-800"}`}><div className="flex flex-wrap items-start justify-between gap-2"><p className="min-w-0 truncate text-sm font-medium text-zinc-100">{page.url}</p><div className="flex gap-2">{page.is_duplicate && <span className="rounded border border-amber-900 px-2 py-0.5 text-xs text-amber-400">Duplicate excluded</span>}<span className="rounded border border-zinc-800 px-2 py-0.5 text-xs text-zinc-500">HTTP {page.status_code || "N/A"}</span></div></div><p className="mt-1 text-sm text-zinc-400">{page.page_title || page.h1 || "Untitled page"}</p><p className="mt-3 text-xs text-zinc-500">{page.word_count} words • {page.internal_link_count} internal references • {page.external_link_count} external references • {page.h1 ? "H1 detected" : "No H1 detected"}</p>{page.is_duplicate && page.duplicate_of_url && <p className="mt-2 text-xs text-amber-500">Identical extracted content to {page.duplicate_of_url}; retained as crawl provenance but excluded from scoring.</p>}</div>; }
function formatScore(score?: number | null) { return score === null || score === undefined ? "Unavailable" : `${score}/100`; }
function formatCategory(category: string) { return category.replaceAll("_", " "); }
function countSuccessfulPages(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.status_code === 200).length; }
function countUniquePages(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.status_code === 200 && !page.is_duplicate).length; }
function countDuplicatePages(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.is_duplicate).length; }
function totalWords(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.status_code === 200 && !page.is_duplicate).reduce((sum, page) => sum + page.word_count, 0); }
