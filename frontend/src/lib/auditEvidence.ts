import type { AuditResult, WebsitePageAudit } from "@/api/audit";

export const PATH_CATEGORIES = {
  "FAQ / help": ["faq", "help", "docs", "questions"],
  "Guide / resource": ["guide", "resource", "learn", "documentation"],
  "About / company": ["about", "company", "team"],
  Comparison: ["compare", "comparison", "versus", "vs"],
  Research: ["research", "study", "evidence"],
  Pricing: ["pricing", "plans"],
  Examples: ["example", "examples", "showcase"],
} as const;

export const TRUST_SIGNALS = {
  "Privacy-related content": ["privacy"],
  "Terms-related content": ["terms", "legal"],
  "Security-related content": ["security", "secure"],
  "Customer / testimonial language": ["customer", "testimonial", "case study"],
  "About / company content": ["about", "company", "team"],
} as const;

export function analyzedPages(audit: AuditResult): WebsitePageAudit[] {
  return (audit.pages || []).filter((page) =>
    !page.is_duplicate &&
    page.status_code !== null &&
    page.status_code >= 200 &&
    page.status_code < 300 &&
    page.word_count > 0,
  );
}

export function buildAuditEvidence(audit: AuditResult) {
  const pages = analyzedPages(audit);
  const totalWords = pages.reduce((sum, page) => sum + page.word_count, 0);
  const internalLinks = pages.reduce((sum, page) => sum + page.internal_link_count, 0);
  const externalLinks = pages.reduce((sum, page) => sum + page.external_link_count, 0);
  const searchablePages = pages.map((page) => ({
    page,
    text: [page.url, page.page_title, page.h1, page.meta_description]
      .filter(Boolean)
      .join(" ")
      .toLowerCase(),
  }));

  return {
    pages,
    totalWords,
    averageWords: pages.length ? Math.round(totalWords / pages.length) : 0,
    pagesWithTitle: pages.filter((page) => Boolean(page.page_title)).length,
    pagesWithH1: pages.filter((page) => Boolean(page.h1)).length,
    pagesWithMeta: pages.filter((page) => Boolean(page.meta_description)).length,
    faqQuestionPages: countMatchingPages(searchablePages, ["faq", "question", "answer"]),
    guideHelpPages: countMatchingPages(searchablePages, ["guide", "help", "docs", "documentation"]),
    internalLinks,
    externalLinks,
    averageInternalLinks: pages.length ? Number((internalLinks / pages.length).toFixed(1)) : 0,
    pathCategories: classify(searchablePages, PATH_CATEGORIES),
    trustSignals: classify(searchablePages, TRUST_SIGNALS),
  };
}

export function pageExclusionReason(page: WebsitePageAudit): string | null {
  if (page.is_duplicate) return `Duplicate content; canonical evidence is ${page.duplicate_of_url || "another crawled URL"}.`;
  if (page.status_code === null) return "No HTTP response was recorded.";
  if (page.status_code < 200 || page.status_code >= 300) return `HTTP ${page.status_code} was not accepted as page evidence.`;
  if (page.word_count === 0) return "No analyzable extracted text was retained from this response.";
  return null;
}

export function formatAbsentSignal(label: string, scope: string): string {
  return `${label} — ${scope}`;
}

type SearchablePage = { page: WebsitePageAudit; text: string };
type RuleMap = Record<string, readonly string[]>;

function countMatchingPages(pages: SearchablePage[], keywords: readonly string[]) {
  return pages.filter(({ text }) => keywords.some((keyword) => text.includes(keyword))).length;
}

function classify(pages: SearchablePage[], rules: RuleMap) {
  return Object.entries(rules).map(([label, keywords]) => ({
    label,
    detected: pages.some(({ text }) => keywords.some((keyword) => text.includes(keyword))),
  }));
}
