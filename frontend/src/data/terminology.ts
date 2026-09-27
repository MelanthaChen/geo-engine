export type TerminologyEntry = {
  label: string;
  description: string;
  detail?: string;
  example?: string;
};

export const terminology = {
  representative_pages: { label: "Representative Pages", description: "A selected subset of discovered pages used to represent the site's major content areas during the audit." },
  urls_discovered: { label: "URLs Discovered", description: "The total number of unique same-site URLs found through the audited URL, sitemap discovery, and internal-link discovery." },
  pages_selected_for_analysis: { label: "Pages Selected for Analysis", description: "The representative pages chosen from the discovered URL inventory for detailed analysis." },
  http_success: { label: "HTTP Success", description: "Pages whose HTTP request returned a successful 2xx response. This does not necessarily mean usable page content was extracted." },
  html_accepted: { label: "HTML Accepted", description: "Successful responses whose content was valid HTML and eligible for content extraction." },
  extraction_success: { label: "Extraction Success", description: "Pages from which meaningful content was successfully extracted." },
  unique_pages: { label: "Unique Pages", description: "Analyzed pages with distinct final content after duplicate and fallback responses are removed." },
  duplicate_fallback: { label: "Duplicate / Fallback", description: "Different URLs that resolved to substantially identical final content and were excluded from duplicate evidence." },
  extraction_method: { label: "Extraction Method", description: "How page content was obtained, such as direct HTTP HTML extraction or JavaScript browser rendering." },
  sitemap: { label: "Sitemap", description: "A machine-readable list of site URLs used to help discover pages." },
  robots_txt: { label: "robots.txt", description: "A site file that provides crawler guidance and may declare sitemap locations." },
  prominent_extracted_terms: { label: "Prominent Extracted Terms", description: "Frequently or prominently observed terms derived from page titles, headings, and content using deterministic extraction." },
  reference_like_links: { label: "Reference-like Links", description: "Outbound links that appear to function as citations, sources, references, or supporting evidence rather than ordinary navigation." },
  qa_pairs: { label: "Q&A Pairs", description: "Explicit question-and-answer structures detected in the page content." },
  faq_page_schema: { label: "FAQPage Schema", description: "Structured data indicating that a page contains FAQ-style question-and-answer content." },

  optimization_opportunity: { label: "Optimization Opportunity", description: "An evidence-backed candidate area where the audited content may benefit from a GEO treatment." },
  recommended_strategy: { label: "Recommended Strategy", description: "The GEO strategy suggested from the current audit evidence. The researcher can override this recommendation." },
  validation_strategy: { label: "Validation Strategy", description: "The strategy selected for the controlled baseline-versus-treatment experiment." },
  baseline: { label: "Original / Baseline", description: "The generated result using the unchanged target content before applying a GEO treatment." },
  treatment: { label: "Treatment", description: "The generated result using the target content after applying the selected GEO strategy." },
  strategy_faq: { label: "FAQ / Q&A Structure", description: "Reorganizes existing source content into explicit questions and grounded answers to improve direct answerability." },
  strategy_statistics: { label: "Statistics", description: "Adds or emphasizes quantitative evidence using information grounded in the source content." },
  strategy_citation: { label: "Citation", description: "Improves explicit source attribution and supporting references using available evidence." },
  strategy_quotation: { label: "Quotation", description: "Uses grounded quotations or attributed statements from the source content." },
  strategy_authoritative: { label: "Authoritative", description: "Strengthens explicit expertise, provenance, evidence, and source attribution without inventing credentials or claims." },
  strategy_technical_terms: { label: "Technical Terms", description: "Emphasizes domain-specific terminology already supported by the source content." },
  strategy_easy_to_understand: { label: "Easy to Understand", description: "Rewrites content for clearer structure and comprehension while preserving meaning." },
  strategy_fluency: { label: "Fluency", description: "Improves wording and flow while preserving the original information." },
  strategy_unique_words: { label: "Unique Words", description: "Encourages more varied vocabulary while preserving the source meaning." },
  strategy_keyword_stuffing: { label: "Keyword Stuffing", description: "A comparison strategy that increases repeated keyword usage. It is included primarily as a research treatment rather than a recommended best practice." },

  geo: { label: "GEO", description: "Generative Engine Optimization: improving content so generative search systems can more effectively discover, understand, cite, and use it." },
  visibility: { label: "Visibility", description: "Measures how prominently the target source appears in the generated answer." },
  pawc: { label: "PAWC", description: "Position-Adjusted Word Count. Measures how much target-source content appears in the generated answer while accounting for where that content appears." },
  citation_count: { label: "Citation Count", description: "The number of generated-answer citations or source references attributed to the target source under the experiment's evaluation method." },
  citation_delta: { label: "Citation Delta", description: "The treatment citation result minus the baseline citation result." },
  visibility_delta: { label: "Visibility Delta", description: "Treatment visibility minus baseline visibility for the same controlled query and source set." },
  word_contribution: { label: "Word Contribution", description: "The amount of generated-answer content attributed to or matched with the target source." },
  source_set: { label: "Source Set", description: "The fixed collection of target and reference sources provided to the generative model for a controlled experiment." },
  target_source: { label: "Target Source", description: "The website or page being optimized and compared between baseline and treatment." },
  reference_sources: { label: "Reference Sources", description: "The unchanged comparison sources included alongside the target in the controlled experiment." },
  frozen_references: { label: "Frozen References", description: "Reference-source snapshots captured once and reused unchanged across baseline and treatment to keep the experiment controlled." },
  live_retrieval: { label: "Live Retrieval", description: "Reference sources obtained from a live search or retrieval provider at experiment setup time, then frozen for that experiment." },

  teacher: { label: "Teacher", description: "The evaluation stage that compares baseline and treatment outputs and records experiment results used to construct training examples." },
  teacher_model: { label: "Teacher Model", description: "The model used to evaluate or generate the recorded Teacher Pipeline result." },
  training_sample: { label: "Training Sample", description: "One distinct query/context experiment containing a baseline result, treatment result, metrics, and provenance." },
  unique_context: { label: "Unique Context", description: "A distinct combination of query, target snapshot, ordered reference source set, target position, and strategy." },
  repetition: { label: "Repetition", description: "An additional stochastic generation using the same experimental context. Repetitions are separate from unique training samples." },
  context_experiment: { label: "Context Experiment", description: "One controlled baseline-versus-treatment experiment for a unique query and source context." },
  dataset_version: { label: "Dataset Version", description: "An immutable version identifier for a generated collection of training-eligible samples." },
  training_eligible: { label: "Training Eligible", description: "Indicates whether a sample is permitted to enter the formal model-training dataset." },
  source_mode: { label: "Source Mode", description: "Describes how the experiment's source context was obtained, such as frozen demo, benchmark, generated query, or live retrieval." },
  provenance: { label: "Provenance", description: "Recorded metadata that allows the sample to be traced back to its query, source snapshots, strategy, experiment, and generation process." },
  context_fingerprint: { label: "Context Fingerprint", description: "A deterministic identifier used to prevent the same experimental context from being counted twice." },

  frozen_demo: { label: "Frozen Demo", description: "A controlled demonstration using a predetermined query and reference-source set for reproducibility. Frozen-demo samples are not automatically included in the formal training dataset." },
  training_dataset: { label: "Training Dataset", description: "The collection of training-eligible, provenance-tracked samples intended for future model training." },
  generated_query: { label: "Generated Query", description: "A query derived from audited website evidence rather than observed from a live search-query log." },
  benchmark_query: { label: "Benchmark Query", description: "A query sourced from a fixed benchmark dataset." },
} as const satisfies Record<string, TerminologyEntry>;

export type TermKey = keyof typeof terminology;

const strategyTerms = {
  original: "baseline",
  faq: "strategy_faq",
  statistics: "strategy_statistics",
  citation: "strategy_citation",
  quotation: "strategy_quotation",
  authoritative: "strategy_authoritative",
  technical_terms: "strategy_technical_terms",
  easy_to_understand: "strategy_easy_to_understand",
  fluency: "strategy_fluency",
  unique_words: "strategy_unique_words",
  keyword_stuffing: "strategy_keyword_stuffing",
} as const satisfies Record<string, TermKey>;

export function strategyTermKey(strategy: string): TermKey | undefined {
  return strategyTerms[strategy as keyof typeof strategyTerms];
}

export const metricTerms = {
  pawc: "pawc",
  citation_count: "citation_count",
  visibility_score: "visibility",
} as const satisfies Record<string, TermKey>;
