import { useEffect, useState } from "react";
import type { ReactNode } from "react";
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
  type WebsitePageAudit,
} from "@/api/audit";
import { EmptyState, Page, PageHeader, SectionHeader } from "@/components/layout/PageLayout";
import { useProperty } from "@/contexts/PropertyContext";
import { buildAuditEvidence, pageExclusionReason } from "@/lib/auditEvidence";

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

      {audit?.status === "insufficient_analyzable_content" && <Card className="border-amber-900 bg-amber-950/30"><CardContent className="p-6"><h2 className="text-lg font-semibold text-amber-100">Insufficient analyzable content</h2><p className="mt-1 text-sm text-amber-200/80">The crawl completed, but no unique HTML page produced usable extracted text. Evidence summaries and optimization opportunities are unavailable for this audit.</p></CardContent></Card>}

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

export function AuditResults({ audit }: { audit: AuditResult }) {
  const coverage = audit.crawl_coverage;
  const opportunities = audit.optimization_opportunities || [];
  const evidence = buildAuditEvidence(audit);
  const analyzedCount = evidence.pages.length;

  return <>
      <section>
        <SectionHeader title="Crawl & Evidence Summary" description="Observed crawl outcomes. HTTP responses, extracted pages, and independent content evidence are reported separately." />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <EvidenceMetric label="URLs discovered" value={coverage?.discovered_urls ?? audit.pages?.length ?? 0} />
          <EvidenceMetric label="URLs requested" value={coverage?.requested_urls ?? audit.pages?.length ?? 0} />
          <EvidenceMetric label="Successful HTTP responses" value={coverage?.successful_responses ?? countSuccessfulPages(audit)} />
          <EvidenceMetric label="Successful HTML responses" value={coverage?.accepted_html_responses ?? "Not recorded"} />
          <EvidenceMetric label="Pages with extracted text" value={coverage?.successful_extractions ?? "Not recorded"} />
          <EvidenceMetric label="Unique pages analyzed" value={coverage?.unique_content_pages ?? analyzedCount} />
          <EvidenceMetric label="Duplicate/fallback responses" value={coverage?.duplicate_fallback_responses ?? countDuplicatePages(audit)} />
          <EvidenceMetric label="Skipped due to limit" value={coverage?.skipped_due_to_limit ?? 0} />
          <EvidenceMetric label="Total unique extracted words" value={evidence.totalWords} />
          <EvidenceMetric label="Inventory source" value={formatInventorySource(coverage?.inventory_source)} />
        </div>
        {coverage && <div className={`mt-3 rounded-lg border px-4 py-3 text-sm ${coverage.truncated ? "border-amber-900 bg-amber-950/30 text-amber-200" : "border-emerald-900 bg-emerald-950/30 text-emerald-200"}`}>{coverage.truncated ? `Capped crawl: ${coverage.skipped_due_to_limit} discovered URLs were not requested because the configured limit is ${coverage.crawl_limit}.` : `Complete discovered inventory: all ${coverage.discovered_urls} URLs were requested using ${coverage.inventory_source === "sitemap" ? "the site sitemap" : "recursive internal-link discovery"}.`}</div>}
      </section>

      {analyzedCount > 0 && <>
        <section>
          <SectionHeader title="Content Evidence" description="Counts from unique pages with usable extracted text. Duplicate and fallback responses are excluded." />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <EvidenceMetric label="Unique pages analyzed" value={analyzedCount} />
            <EvidenceMetric label="Total extracted words" value={evidence.totalWords} />
            <EvidenceMetric label="Average words per page" value={evidence.averageWords} />
            <EvidenceMetric label="Titles found" value={`${evidence.pagesWithTitle} / ${analyzedCount} pages`} />
            <EvidenceMetric label="H1 headings found" value={`${evidence.pagesWithH1} / ${analyzedCount} pages`} />
            <EvidenceMetric label="Meta descriptions found" value={`${evidence.pagesWithMeta} / ${analyzedCount} pages`} />
            <EvidenceMetric label="FAQ / question signals" value={`${evidence.faqQuestionPages} / ${analyzedCount} pages`} />
            <EvidenceMetric label="Guide / help / docs signals" value={`${evidence.guideHelpPages} / ${analyzedCount} pages`} />
          </div>
          <p className="mt-3 text-xs leading-5 text-zinc-600">FAQ and guide counts reflect terms found in stored URLs, titles, H1 headings, and metadata.</p>
        </section>

        <section className="grid gap-4 xl:grid-cols-2">
          <EvidencePanel title="Site Structure Evidence" description="Observed links, discovery files, and page-path categories; no quality score is applied.">
            <EvidenceRows rows={[
              ["Internal links found", evidence.internalLinks],
              ["External links found", evidence.externalLinks],
              ["Average internal links per page", evidence.averageInternalLinks],
              ["Sitemap detected", formatBoolean(coverage?.sitemap_detected)],
              ["robots.txt detected", formatBoolean(coverage?.robots_txt_detected)],
              ["Sitemap URLs discovered", coverage?.sitemap_url_count ?? "Not recorded separately"],
              ["Distinct content URLs analyzed", analyzedCount],
            ]} />
            <SignalList signals={evidence.pathCategories} />
          </EvidencePanel>
          <EvidencePanel title="Trust / Legal Signals" description="Terms or paths detected in stored URL, title, heading, and metadata evidence. This is not a measurement of authority, reputation, or backlinks.">
            <SignalList signals={evidence.trustSignals} />
          </EvidencePanel>
        </section>
      </>}

      <section className="grid gap-4 xl:grid-cols-2">
        <FindingPanel title="Strengths" description="Positive characteristics directly supported by crawled evidence." findings={audit.strengths || []} tone="positive" emptyText="No objective strengths are available yet." />
        <FindingPanel title="Weaknesses" description="Observed gaps or missing evidence; no impact is implied." findings={audit.weaknesses || []} tone="negative" emptyText="No objective weaknesses are available yet." />
      </section>

      {analyzedCount > 0 && <section>
        <SectionHeader title="Optimization Opportunities" description="Candidate directions derived from audit findings. These opportunities are not validated improvements and contain no predicted gain." />
        <div className="space-y-3">
          {opportunities.map((opportunity) => <OpportunityRow key={opportunity.id} opportunity={opportunity} />)}
          {!opportunities.length && <EmptyState>No candidate optimization directions are available for this audit.</EmptyState>}
        </div>
      </section>}

      <section>
        <SectionHeader title="Crawled Page Evidence" description="Page-level observations retained by the latest audit." />
        <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-6"><div className="space-y-2">
          {(audit.pages || []).map((page) => <PageAuditRow key={page.id} page={page} />)}
          {(!audit.pages || !audit.pages.length) && <EmptyState>No crawled pages are stored yet. Run an audit to populate page-level evidence.</EmptyState>}
        </div></CardContent></Card>
      </section>
    </>;
}

function EvidencePanel({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-6"><h2 className="text-lg font-semibold text-zinc-50">{title}</h2><p className="mt-1 text-sm leading-6 text-zinc-500">{description}</p><div className="mt-5 space-y-5">{children}</div></CardContent></Card>;
}

function EvidenceRows({ rows }: { rows: Array<[string, string | number]> }) {
  return <div className="divide-y divide-zinc-900 rounded-lg border border-zinc-800 bg-black">{rows.map(([label, value]) => <div className="flex items-center justify-between gap-4 px-4 py-3" key={label}><span className="text-sm text-zinc-500">{label}</span><span className="text-sm font-medium text-zinc-200">{value}</span></div>)}</div>;
}

function SignalList({ signals }: { signals: Array<{ label: string; detected: boolean }> }) {
  const detected = signals.filter((signal) => signal.detected);
  const absent = signals.filter((signal) => !signal.detected);
  return <div className="grid gap-4 sm:grid-cols-2"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-500">Detected terms/signals</p><ul className="mt-2 space-y-2 text-sm text-zinc-300">{detected.map((signal) => <li key={signal.label}>• {signal.label}</li>)}{!detected.length && <li className="text-zinc-600">None detected</li>}</ul></div><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-600">Not detected</p><ul className="mt-2 space-y-2 text-sm text-zinc-500">{absent.map((signal) => <li key={signal.label}>• {signal.label}</li>)}{!absent.length && <li>None</li>}</ul></div></div>;
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
function PageAuditRow({ page }: { page: WebsitePageAudit }) { const exclusion = pageExclusionReason(page); return <details className={`group rounded-lg border bg-black ${exclusion ? "border-amber-950/80" : "border-zinc-800"}`}><summary className="cursor-pointer list-none p-4 [&::-webkit-details-marker]:hidden"><div className="flex flex-wrap items-start justify-between gap-2"><p className="min-w-0 truncate text-sm font-medium text-zinc-100">{page.url}</p><div className="flex gap-2">{exclusion && <span className="rounded border border-amber-900 px-2 py-0.5 text-xs text-amber-400">Excluded</span>}<span className="rounded border border-zinc-800 px-2 py-0.5 text-xs text-zinc-500">HTTP {page.status_code ?? "N/A"}</span></div></div><p className="mt-1 text-sm text-zinc-400">{page.page_title || "No title detected"}</p><p className="mt-1 text-xs text-zinc-500">H1: {page.h1 || "Not detected"}</p><p className="mt-3 text-xs text-zinc-500">{page.word_count} extracted words • {page.internal_link_count} internal links • {page.external_link_count} external links</p>{exclusion && <p className="mt-2 text-xs text-amber-500">{exclusion}</p>}</summary><div className="border-t border-zinc-900 px-4 py-3 text-xs text-zinc-600">Content SHA-256: {page.content_sha256 || "Not produced"}</div></details>; }
function formatCategory(category: string) { return category.replaceAll("_", " "); }
function formatBoolean(value?: boolean | null) { return value === true ? "Yes" : value === false ? "No" : "Not recorded"; }
function formatInventorySource(value?: string) { return value === "sitemap" ? "Sitemap" : value === "recursive_links" ? "Recursive links" : value === "legacy" ? "Legacy / not recorded" : "Not recorded"; }
function countSuccessfulPages(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.status_code !== null && page.status_code >= 200 && page.status_code < 300).length; }
function countDuplicatePages(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.is_duplicate).length; }
