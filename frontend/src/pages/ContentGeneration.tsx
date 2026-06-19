import { useCallback, useEffect, useState } from "react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import { generateContent } from "@/api/content";
import { getContentStatus } from "@/api/contentStatus";
import { generateFaqs } from "@/api/faq";
import { fetchContentHistory } from "@/api/history";
import { publishContent } from "@/api/publishing";

const contentTypes = [
  { value: "comparison", label: "comparison" },
  { value: "educational", label: "educational" },
  { value: "discussion", label: "discussion" },
  { value: "guide", label: "guide" },
  { value: "opinion", label: "opinion" },
  { value: "reddit_post", label: "reddit_post" },
  { value: "faq_post", label: "faq_post" },
  { value: "blog_post", label: "blog_post" },
  { value: "review", label: "review" },
  { value: "case_study", label: "case_study" },
  { value: "buying_guide", label: "buying_guide" },
  { value: "alternatives", label: "alternatives" },
  { value: "best_of", label: "best_of" },
  { value: "community_summary", label: "community_summary" },
  { value: "experience_report", label: "experience_report" },
];

function formatPublishStatus(status: string) {
  if (status === "review_ready") {
    return "Review Ready";
  }

  return status;
}

function statusClass(status: string) {
  if (status === "published") {
    return "text-green-400";
  }

  if (status === "review_ready") {
    return "text-emerald-300";
  }

  if (status === "queued") {
    return "text-yellow-400";
  }

  if (status === "pending") {
    return "text-blue-400";
  }

  if (status === "failed") {
    return "text-red-400";
  }

  return "text-zinc-400";
}

export function ContentGeneration() {
  const [query, setQuery] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [persona, setPersona] = useState("student");
  const [contentType, setContentType] = useState("comparison");
  const [publishPlatform, setPublishPlatform] = useState("reddit");
  const [loading, setLoading] = useState(false);
  const [aiGeneratedContent, setAiGeneratedContent] = useState("");
  const [platformGeneratedContent, setPlatformGeneratedContent] = useState("");
  const [aiFaqs, setAiFaqs] = useState("");
  const [platformFaqs, setPlatformFaqs] = useState("");
  const [aiContentId, setAiContentId] = useState<number | null>(null);
  const [platformContentId, setPlatformContentId] = useState<number | null>(
    null,
  );
  const [aiStatus, setAiStatus] = useState("draft");
  const [platformStatus, setPlatformStatus] = useState("draft");
  const [aiUrl, setAiUrl] = useState("");
  const [platformUrl, setPlatformUrl] = useState("");
  const reviewBannerVisible =
    aiStatus === "review_ready" || platformStatus === "review_ready";

  const refreshStatus = useCallback(async () => {
    try {
      if (aiContentId) {
        const data = await getContentStatus(aiContentId);

        setAiStatus(data.publish_status);
        setAiUrl(data.published_url || "");
      }

      if (platformContentId) {
        const data = await getContentStatus(platformContentId);

        setPlatformStatus(data.publish_status);
        setPlatformUrl(data.published_url || "");
      }
    } catch (error) {
      console.error(error);
    }
  }, [aiContentId, platformContentId]);

  useEffect(() => {
    const interval = setInterval(refreshStatus, 5000);

    return () => clearInterval(interval);
  }, [refreshStatus]);

  async function handleGenerateAiFaqs() {
    try {
      setLoading(true);

      const result = await generateFaqs(query, "ai", contentType, targetUrl);

      setAiFaqs(result.faqs);

      return {
        faqs: result.faqs,
        faqSetId: result.faq_set_id || null,
      };
    } catch (error) {
      console.error(error);
      alert("Failed to generate AI FAQs");

      return {
        faqs: "",
        faqSetId: null,
      };
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePlatformFaqs() {
    try {
      setLoading(true);

      const result = await generateFaqs(
        query,
        "platform",
        contentType,
        targetUrl,
      );

      setPlatformFaqs(result.faqs);

      return {
        faqs: result.faqs,
        faqSetId: result.faq_set_id || null,
      };
    } catch (error) {
      console.error(error);
      alert("Failed to generate platform FAQs");

      return {
        faqs: "",
        faqSetId: null,
      };
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePackage() {
    setLoading(true);

    try {
      const aiFaqResult = await handleGenerateAiFaqs();
      const platformFaqResult = await handleGeneratePlatformFaqs();

      const aiResult = await generateContent(
        query,
        persona,
        contentType,
        targetUrl,
        "ai",
        aiFaqResult.faqs,
        "",
        "ai_faq",
        aiFaqResult.faqSetId,
      );

      setAiGeneratedContent(aiResult.generated_content);
      setAiContentId(aiResult.content_id);
      setAiStatus("draft");
      setAiUrl("");

      const platformResult = await generateContent(
        query,
        persona,
        contentType,
        targetUrl,
        "platform",
        "",
        platformFaqResult.faqs,
        "platform_faq",
        platformFaqResult.faqSetId,
      );

      setPlatformGeneratedContent(platformResult.generated_content);
      setPlatformContentId(platformResult.content_id);
      setPlatformStatus("draft");
      setPlatformUrl("");

      await fetchContentHistory();
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  async function handlePublish(contentId: number) {
    try {
      if (contentId === aiContentId) {
        setAiStatus("queued");
      }

      if (contentId === platformContentId) {
        setPlatformStatus("queued");
      }

      const result = await publishContent(contentId, publishPlatform);

      if (result.error) {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error(error);

      alert(
        error instanceof Error
          ? error.message
          : "Failed to queue content for publishing",
      );

      if (contentId === aiContentId) {
        setAiStatus("failed");
      }

      if (contentId === platformContentId) {
        setPlatformStatus("failed");
      }
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Workflow
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Content Generation
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Discover category FAQs, generate source-aware content, and queue
          publishing tasks.
        </p>
      </div>

      {reviewBannerVisible && (
        <div className="rounded-lg border border-emerald-500 bg-emerald-950 px-5 py-4 font-semibold text-emerald-100">
          Human Review Required
        </div>
      )}

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="grid gap-4 p-6 lg:grid-cols-5">
          <label className="space-y-2 lg:col-span-2">
            <span className="text-sm text-zinc-400">Category</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="AI Resume Builder"
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
            />
          </label>

          <label className="space-y-2 lg:col-span-2">
            <span className="text-sm text-zinc-400">Website URL</span>
            <input
              value={targetUrl}
              onChange={(event) => setTargetUrl(event.target.value)}
              placeholder="https://example.com"
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
            />
          </label>

          <label className="space-y-2">
            <span className="text-sm text-zinc-400">Persona</span>
            <select
              value={persona}
              onChange={(event) => setPersona(event.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
            >
              <option>student</option>
              <option>engineering student</option>
              <option>medical student</option>
              <option>productivity enthusiast</option>
              <option>researcher</option>
            </select>
          </label>

          <label className="space-y-2 lg:col-span-2">
            <span className="text-sm text-zinc-400">Content Type</span>
            <select
              value={contentType}
              onChange={(event) => setContentType(event.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
            >
              {contentTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 lg:col-span-2">
            <span className="text-sm text-zinc-400">Publish Platform</span>
            <select
              value={publishPlatform}
              onChange={(event) => setPublishPlatform(event.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
            >
              <option>reddit</option>
              <option>xiaohongshu</option>
              <option>wordpress</option>
              <option>github_pages</option>
              <option>medium</option>
            </select>
          </label>

          <div className="flex items-end">
            <Button
              className="w-full"
              disabled={loading}
              onClick={handleGeneratePackage}
            >
              {loading ? "Generating..." : "Generate Content"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <FaqPanel title="AI FAQs" value={aiFaqs || "No AI FAQs yet."} />
        <FaqPanel
          title="Platform FAQs"
          value={platformFaqs || "No platform FAQs yet."}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ContentPanel
          body={aiGeneratedContent || "No AI-generated content yet."}
          contentId={aiContentId}
          onPublish={handlePublish}
          status={aiStatus}
          title="AI FAQ-Based Content"
          url={aiUrl}
        />
        <ContentPanel
          body={
            platformGeneratedContent || "No platform-generated content yet."
          }
          contentId={platformContentId}
          onPublish={handlePublish}
          status={platformStatus}
          title="Platform FAQ-Based Content"
          url={platformUrl}
        />
      </div>
    </div>
  );
}

type FaqPanelProps = {
  title: string;
  value: string;
};

function FaqPanel({ title, value }: FaqPanelProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="flex h-[430px] flex-col p-6">
        <h2 className="mb-4 text-xl font-semibold text-zinc-50">{title}</h2>
        <div className="flex-1 overflow-y-auto whitespace-pre-wrap rounded-xl border border-zinc-800 bg-black p-4 text-sm text-zinc-300">
          {value}
        </div>
      </CardContent>
    </Card>
  );
}

type ContentPanelProps = {
  body: string;
  contentId: number | null;
  onPublish: (contentId: number) => void;
  status: string;
  title: string;
  url: string;
};

function ContentPanel({
  body,
  contentId,
  onPublish,
  status,
  title,
  url,
}: ContentPanelProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="flex h-[560px] flex-col p-6">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-zinc-50">{title}</h2>
            <div className="mt-2 flex items-center gap-3 text-sm">
              <span className="text-zinc-500">Status</span>
              <span className={`font-semibold ${statusClass(status)}`}>
                {formatPublishStatus(status).toUpperCase()}
              </span>
              {url && (
                <a
                  className="text-blue-400 underline hover:text-blue-300"
                  href={url}
                  rel="noreferrer"
                  target="_blank"
                >
                  View Post
                </a>
              )}
            </div>
          </div>

          <Button
            disabled={!contentId}
            onClick={() => contentId && onPublish(contentId)}
            size="sm"
          >
            Publish
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto whitespace-pre-wrap rounded-xl border border-zinc-800 bg-black p-4 text-sm leading-6 text-zinc-300">
          {body}
        </div>
      </CardContent>
    </Card>
  );
}
