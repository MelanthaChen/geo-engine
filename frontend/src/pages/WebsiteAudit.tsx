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
import { buildAuditEvidence, formatAbsentSignal, pageExclusionReason } from "@/lib/auditEvidence";

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
          <EvidenceMetric label="Representative pages selected" value={coverage?.selected_urls ?? audit.pages?.length ?? 0} />
          <EvidenceMetric label="URLs requested" value={coverage?.requested_urls ?? audit.pages?.length ?? 0} />
          <EvidenceMetric label="Successful HTTP responses" value={coverage?.successful_responses ?? countSuccessfulPages(audit)} />
          <EvidenceMetric label="Successful HTML responses" value={coverage?.accepted_html_responses ?? "Not recorded"} />
          <EvidenceMetric label="Pages with extracted text" value={coverage?.successful_extractions ?? "Not recorded"} />
          <EvidenceMetric label="HTTP-only pages" value={coverage?.http_extracted_pages ?? "Not recorded"} />
          <EvidenceMetric label="Browser-rendered pages" value={coverage?.browser_extracted_pages ?? "Not recorded"} />
          <EvidenceMetric label="Extraction failures" value={coverage?.extraction_failures ?? "Not recorded"} />
          <EvidenceMetric label="Unique pages analyzed" value={coverage?.unique_content_pages ?? analyzedCount} />
          <EvidenceMetric label="Duplicate/fallback responses" value={coverage?.duplicate_fallback_responses ?? countDuplicatePages(audit)} />
          <EvidenceMetric label="Not selected for standard audit" value={coverage?.not_selected_due_to_sampling ?? 0} />
          <EvidenceMetric label="Skipped by hard safety limit" value={coverage?.skipped_due_to_limit ?? 0} />
          <EvidenceMetric label="Total unique extracted words" value={evidence.totalWords} />
          <EvidenceMetric label="Inventory source" value={formatInventorySource(coverage?.inventory_source)} />
        </div>
        {coverage && <CoverageNotice coverage={coverage} />}
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

        {Boolean(audit.strategy_evidence_summary?.analyzed_pages) && <StrategyEvidenceSummary audit={audit} />}

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
            <SignalList signals={evidence.pathCategories} absentTitle="Page types not observed" absentSuffix="Not observed in analyzed evidence" />
          </EvidencePanel>
          <EvidencePanel title="Trust / Legal Signals" description="Terms or paths detected in stored URL, title, heading, and metadata evidence. This is not a measurement of authority, reputation, or backlinks.">
            <SignalList signals={evidence.trustSignals} absentTitle="Not detected in analyzed evidence" absentSuffix="Not detected in analyzed evidence" />
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

function CoverageNotice({ coverage }: { coverage: NonNullable<AuditResult["crawl_coverage"]> }) {
  if (coverage.sampling_applied) {
    return <div className="mt-3 rounded-lg border border-blue-900 bg-blue-950/30 px-4 py-3 text-sm text-blue-200">Representative website audit: {coverage.selected_urls} pages selected from {coverage.discovered_urls} discovered URLs. {coverage.not_selected_due_to_sampling} URLs were not selected for the standard audit sample.{coverage.truncated ? ` A further ${coverage.skipped_due_to_limit} eligible pages were blocked by the ${coverage.crawl_limit}-page hard safety limit.` : ""}</div>;
  }
  if (coverage.truncated) {
    return <div className="mt-3 rounded-lg border border-amber-900 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">Safety-capped audit: {coverage.skipped_due_to_limit} eligible URLs were not requested because the hard limit is {coverage.crawl_limit}.</div>;
  }
  return <div className="mt-3 rounded-lg border border-emerald-900 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-200">Complete discovered inventory coverage: all {coverage.discovered_urls} discovered URLs fit within the {coverage.sample_page_limit ?? coverage.crawl_limit}-page standard audit size.</div>;
}

function EvidencePanel({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <Card className="border-zinc-800 bg-zinc-950"><CardContent className="p-6"><h2 className="text-lg font-semibold text-zinc-50">{title}</h2><p className="mt-1 text-sm leading-6 text-zinc-500">{description}</p><div className="mt-5 space-y-5">{children}</div></CardContent></Card>;
}

function EvidenceRows({ rows }: { rows: Array<[string, string | number]> }) {
  return <div className="divide-y divide-zinc-900 rounded-lg border border-zinc-800 bg-black">{rows.map(([label, value]) => <div className="flex items-center justify-between gap-4 px-4 py-3" key={label}><span className="text-sm text-zinc-500">{label}</span><span className="text-sm font-medium text-zinc-200">{value}</span></div>)}</div>;
}

function SignalList({ signals, absentTitle = "Not detected", absentSuffix }: { signals: Array<{ label: string; detected: boolean }>; absentTitle?: string; absentSuffix?: string }) {
  const detected = signals.filter((signal) => signal.detected);
  const absent = signals.filter((signal) => !signal.detected);
  return <div className="grid gap-4 sm:grid-cols-2"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-500">Detected terms/signals</p><ul className="mt-2 space-y-2 text-sm text-zinc-300">{detected.map((signal) => <li key={signal.label}>• {signal.label}</li>)}{!detected.length && <li className="text-zinc-600">None detected</li>}</ul></div><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-600">{absentTitle}</p><ul className="mt-2 space-y-2 text-sm text-zinc-500">{absent.map((signal) => <li key={signal.label}>• {absentSuffix ? formatAbsentSignal(signal.label, absentSuffix) : signal.label}</li>)}{!absent.length && <li>None</li>}</ul></div></div>;
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
    <div className="border-t border-zinc-800 px-5 py-5"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">Observed evidence</p><p className="mt-2 text-sm leading-6 text-zinc-300">{opportunity.observed_evidence || opportunity.evidence}</p><p className="mt-3 text-xs text-zinc-500">Affected pages or URLs: {opportunity.affected_page_count} of {opportunity.evaluated_page_count}</p>{opportunity.suggested_strategy && <p className="mt-2 text-xs text-zinc-500">Suggested strategy: <span className="text-zinc-300">{formatCategory(opportunity.suggested_strategy)}</span></p>}{Boolean(opportunity.affected_urls?.length) && <details className="mt-3 rounded-lg border border-zinc-800 bg-black/50 p-3"><summary className="cursor-pointer text-xs text-blue-400">View affected pages</summary><ul className="mt-2 space-y-1 text-xs text-zinc-500">{opportunity.affected_urls?.map((url) => <li className="break-all" key={url}>• {url}</li>)}</ul></details>}<p className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">Why it may matter</p><p className="mt-2 text-sm leading-6 text-zinc-300">{opportunity.why_it_matters}</p>
      {opportunity.evidence_url && <a className="mt-3 inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300" href={opportunity.evidence_url} target="_blank" rel="noreferrer">View observed page <ExternalLink className="h-3 w-3" /></a>}
      <div className="mt-4 rounded-lg border border-zinc-800 bg-black/60 px-4 py-3 text-xs leading-5 text-zinc-500">Generated from objective audit findings, not from a prediction model. No impact or visibility gain has been estimated.</div>
    </div>
  </details>;
}

function Tag({ children }: { children: string }) { return <span className="rounded-full border border-zinc-800 px-2 py-0.5 text-[10px] uppercase tracking-wide text-zinc-500">{children}</span>; }
function EvidenceMetric({ label, value }: { label: string; value: string | number }) { return <div className="rounded-lg border border-zinc-800 bg-zinc-950 px-4 py-3"><p className="text-xs text-zinc-500">{label}</p><p className="mt-1 truncate text-sm font-medium text-zinc-200">{value}</p></div>; }
function StrategyEvidenceSummary({ audit }: { audit: AuditResult }) {
  const summary = audit.strategy_evidence_summary!;
  const total = summary.analyzed_pages;
  const schemas = Object.entries(summary.structured_data);
  return <section><SectionHeader title="Strategy-Relevant Evidence" description="Deterministic facts derived from the same admitted page evidence. These are not scores or predicted gains." /><div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
    <EvidencePanel title="FAQ / Q&A" description="Observed question structure and FAQ structured data."><EvidenceRows rows={[["Pages with question headings", `${summary.faq.pages_with_question_headings} / ${total}`], ["Pages with Q&A pairs", `${summary.faq.pages_with_qa_pairs} / ${total}`], ["Pages with FAQPage schema", `${summary.faq.pages_with_faq_schema} / ${total}`], ["Explanatory pages without Q&A", summary.faq.explanatory_pages_without_qa]]} /></EvidencePanel>
    <EvidencePanel title="Statistics" description="Numeric evidence is detected, not fact-checked."><EvidenceRows rows={[["Pages with numeric claims", `${summary.statistics.pages_with_numeric_claims} / ${total}`], ["Quantitative statements", summary.statistics.quantitative_statements]]} /></EvidencePanel>
    <EvidencePanel title="Citations" description="Reference-like links are separated from generic external links."><EvidenceRows rows={[["Pages with reference links", `${summary.citations.pages_with_reference_links} / ${total}`], ["Reference-like links", summary.citations.reference_like_links], ["Distinct reference domains", summary.citations.distinct_reference_domains.length]]} /></EvidencePanel>
    <EvidencePanel title="Authorship / Dates" description="Only explicitly detected authorship and date metadata."><EvidenceRows rows={[["Pages exposing an author", `${summary.authorship.pages_with_author} / ${total}`], ["Pages exposing dates", `${summary.authorship.pages_with_dates} / ${total}`]]} /></EvidencePanel>
    <EvidencePanel title="Quotations" description="Blockquotes and explicit quoted passages."><EvidenceRows rows={[["Pages with quotations", `${summary.quotations.pages_with_quotations} / ${total}`]]} /></EvidencePanel>
    <EvidencePanel title="Structured Data" description="JSON-LD schema types observed in analyzed pages.">{schemas.length ? <EvidenceRows rows={schemas} /> : <p className="text-sm text-zinc-600">No JSON-LD schema types detected.</p>}</EvidencePanel>
  </div></section>;
}

function PageAuditRow({ page }: { page: WebsitePageAudit }) {
  const exclusion = pageExclusionReason(page);
  const evidence = page.evidence;
  const strategies = evidence?.strategies || {};
  const faq = strategies.faq || {};
  const statistics = strategies.statistics || {};
  const citation = strategies.citation || {};
  const quotation = strategies.quotation || {};
  const authoritative = strategies.authoritative || {};
  const readability = strategies.easy_to_understand || {};
  const uniqueWords = strategies.unique_words || {};
  const keywordEvidence = strategies.keyword_stuffing || {};
  const extraction = page.extraction_method === "browser" ? "JavaScript-rendered browser fallback" : page.extraction_method === "failed" ? "Unavailable" : page.extraction_method === "http" ? "HTTP HTML" : "Not recorded";
  const prominentTerms = asStrings((strategies.technical_terms || {}).prominent_terms);
  const referenceLinks = evidence?.links?.reference_like_links || [];
  return <details className={`group rounded-lg border bg-black ${exclusion ? "border-amber-950/80" : "border-zinc-800"}`}>
    <summary className="cursor-pointer list-none p-4 [&::-webkit-details-marker]:hidden">
      <div className="flex flex-wrap items-start justify-between gap-2"><div className="min-w-0"><p className="text-sm font-medium text-zinc-100">{page.page_title || "No title detected"}</p><p className="mt-1 break-all text-xs text-zinc-500">{page.url}</p></div><div className="flex gap-2">{exclusion && <span className="rounded border border-amber-900 px-2 py-0.5 text-xs text-amber-400">Excluded</span>}<span className="rounded border border-zinc-800 px-2 py-0.5 text-xs text-zinc-500">Extraction: {extraction}</span></div></div>
      <p className="mt-3 text-xs text-zinc-400">{page.word_count.toLocaleString()} words • H1 {page.h1 ? "✓" : "not detected"} • Meta {page.meta_description ? "✓" : "not detected"}</p>
      <p className="mt-2 text-xs text-zinc-500">Prominent extracted terms: {prominentTerms.length ? prominentTerms.join(", ") : "Not detected"}</p>
      <p className="mt-2 text-xs text-zinc-500">Strategy evidence: FAQ {numberValue(faq.detected_qa_pair_count)} Q&A pairs • Statistics {numberValue(statistics.numeric_claim_count)} numeric claims • Citations {numberValue(citation.reference_like_link_count)} reference links</p>
      {exclusion && <p className="mt-2 text-xs text-amber-500">Reason: {exclusion}</p>}
    </summary>
    <div className="space-y-5 border-t border-zinc-900 px-4 py-4 text-xs text-zinc-500">
      <EvidenceRows rows={[["Requested URL", evidence?.identity?.requested_url || page.url], ["Final URL", evidence?.identity?.final_url || page.url], ["Canonical", evidence?.identity?.canonical_url || "Not detected"], ["Path family", evidence?.identity?.path_family || "Not recorded"], ["Robots directives", evidence?.metadata?.robots_directives?.join(", ") || "Not detected"]]} />
      <EvidenceBlock title="Headings" values={[...(evidence?.headings?.h1 || []).map((value) => `H1: ${value}`), ...(evidence?.headings?.h2 || []).map((value) => `H2: ${value}`), ...(evidence?.headings?.h3 || []).map((value) => `H3: ${value}`)]} />
      <EvidenceBlock title="Content preview" values={evidence?.content?.preview ? [evidence.content.preview] : []} />
      <EvidenceRows rows={[["Paragraphs", evidence?.content?.paragraph_count ?? "Not recorded"], ["Lists", evidence?.content?.list_count ?? "Not recorded"], ["Internal links", evidence?.links?.internal_urls?.length ?? page.internal_link_count], ["External links", evidence?.links?.external_urls?.length ?? page.external_link_count], ["Reference-like links", referenceLinks.length], ["External reference domains", evidence?.links?.reference_domains?.join(", ") || "None detected"]]} />
      <EvidenceBlock title="Reference-like links" values={referenceLinks.map((link) => `${link.anchor_text || link.domain}: ${link.url}`)} />
      <EvidenceRows rows={[["Question headings", numberValue(faq.question_heading_count)], ["Detected Q&A pairs", numberValue(faq.detected_qa_pair_count)], ["FAQPage schema", booleanEvidence(faq.faq_page_schema_present)], ["Numeric claims", numberValue(statistics.numeric_claim_count)], ["Percentages", numberValue(statistics.percentage_count)], ["Currency values", numberValue(statistics.currency_value_count)], ["Quotations", numberValue(quotation.quoted_passage_count) + numberValue(quotation.blockquote_count)], ["Average sentence words", scalarValue(readability.average_sentence_words)], ["Unique tokens", scalarValue(uniqueWords.unique_token_count)], ["Lexical diversity", scalarValue(uniqueWords.lexical_diversity_ratio)], ["Top-term concentration", scalarValue(keywordEvidence.top_term_concentration)]]} />
      <EvidenceBlock title="Quantitative evidence snippets" values={asStrings(statistics.quantitative_snippets)} />
      <EvidenceBlock title="Quotation / attribution evidence" values={[...asStrings(quotation.quote_snippets), ...asStrings(quotation.attribution_snippets)]} />
      <EvidenceBlock title="Highest-frequency meaningful terms" values={formatTermCounts(keywordEvidence.highest_frequency_terms)} />
      <EvidenceBlock title="Repeated phrases" values={formatPhraseCounts(keywordEvidence.repeated_phrases)} />
      <EvidenceRows rows={[["Methodology / research phrases", numberValue(authoritative.methodology_language_count)], ["Explicit credential phrases", numberValue(authoritative.credentials_language_count)], ["Source-attribution phrases", numberValue(citation.attribution_phrase_count)]]} />
      <EvidenceRows rows={[["Schema types", evidence?.structured_data?.schema_types?.join(", ") || "Not detected"], ["Author", evidence?.authorship?.author_name || "Not detected"], ["Published", evidence?.authorship?.published_date || "Not detected"], ["Modified", evidence?.authorship?.modified_date || "Not detected"]]} />
      <p className="text-[11px] text-zinc-700">Content SHA-256: {page.content_sha256 || "Not produced"}</p>
    </div>
  </details>;
}

function EvidenceBlock({ title, values }: { title: string; values: string[] }) { return <div><p className="font-semibold uppercase tracking-[0.14em] text-zinc-600">{title}</p>{values.length ? <ul className="mt-2 space-y-1 text-zinc-400">{values.map((value, index) => <li className="break-words" key={`${title}-${index}`}>• {value}</li>)}</ul> : <p className="mt-2 text-zinc-700">Not detected</p>}</div>; }
function asStrings(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []; }
function formatTermCounts(value: unknown): string[] { return Array.isArray(value) ? value.flatMap((item) => typeof item === "object" && item !== null && "term" in item && "count" in item ? [`${String(item.term)} — ${String(item.count)} occurrences`] : []) : []; }
function formatPhraseCounts(value: unknown): string[] { return Array.isArray(value) ? value.flatMap((item) => typeof item === "object" && item !== null && "phrase" in item && "count" in item ? [`${String(item.phrase)} — ${String(item.count)} occurrences`] : []) : []; }
function numberValue(value: unknown): number { return typeof value === "number" ? value : 0; }
function scalarValue(value: unknown): string | number { return typeof value === "number" || typeof value === "string" ? value : "Not recorded"; }
function booleanEvidence(value: unknown): string { return value === true ? "Yes" : value === false ? "No" : "Not recorded"; }
function formatCategory(category: string) { return category.replaceAll("_", " "); }
function formatBoolean(value?: boolean | null) { return value === true ? "Yes" : value === false ? "No" : "Not recorded"; }
function formatInventorySource(value?: string) { return value === "sitemap" ? "Sitemap" : value === "recursive_links" ? "Recursive links" : value === "legacy" ? "Legacy / not recorded" : "Not recorded"; }
function countSuccessfulPages(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.status_code !== null && page.status_code >= 200 && page.status_code < 300).length; }
function countDuplicatePages(audit: AuditResult | null) { return (audit?.pages || []).filter((page) => page.is_duplicate).length; }
