import { useCallback, useEffect, useState } from "react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import { generateContent } from "@/api/content";
import { getContentStatus } from "@/api/contentStatus";
import {
  generateFaqs,
  getRetrievalTask,
  type PlatformQuestion,
} from "@/api/faq";
import { publishContent } from "@/api/publishing";
import {
  fetchPublishingTasks,
  type PublishingTask,
} from "@/api/publishingQueue";
import { LlmProviderSelector } from "@/components/LlmProviderSelector";
import type { Property } from "@/api/properties";
import type { LlmProvider } from "@/types/experimentLab";
import { useProperty } from "@/contexts/PropertyContext";
import { Page, PageHeader, ResponsiveGrid } from "@/components/layout/PageLayout";

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

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function formatFaqResponseText(result: {
  faqs?: string;
  faq_set?: { questions?: string[] } | null;
}) {
  if (result.faqs?.trim()) {
    return result.faqs;
  }

  const questions = result.faq_set?.questions || [];

  return questions
    .map((question, index) => `${index + 1}. ${question}`)
    .join("\n");
}

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
  const { activeProperty } = useProperty();

  return (
    <ContentGenerationWorkspace
      key={activeProperty?.id || "no-property"}
      activeProperty={activeProperty}
    />
  );
}

function ContentGenerationWorkspace({
  activeProperty,
}: {
  activeProperty: Property | null;
}) {
  const [query, setQuery] = useState("");
  const [persona, setPersona] = useState("student");
  const [contentType, setContentType] = useState("comparison");
  const [publishPlatform, setPublishPlatform] = useState("reddit");
  const [provider, setProvider] = useState<LlmProvider>("chatgpt");
  const [loading, setLoading] = useState(false);
  const [aiGeneratedContent, setAiGeneratedContent] = useState("");
  const [platformGeneratedContent, setPlatformGeneratedContent] = useState("");
  const [aiFaqs, setAiFaqs] = useState("");
  const [platformQuestions, setPlatformQuestions] = useState<
    PlatformQuestion[]
  >([]);
  const isXiaohongshu = publishPlatform === "xiaohongshu";
  const [aiContentId, setAiContentId] = useState<number | null>(null);
  const [platformContentId, setPlatformContentId] = useState<number | null>(
    null,
  );
  const [aiStatus, setAiStatus] = useState("draft");
  const [platformStatus, setPlatformStatus] = useState("draft");
  const [aiUrl, setAiUrl] = useState("");
  const [platformUrl, setPlatformUrl] = useState("");
  const [workflowMessage, setWorkflowMessage] = useState("");
  const [publishTasks, setPublishTasks] = useState<PublishingTask[]>([]);
  const reviewBannerVisible =
    aiStatus === "review_ready" || platformStatus === "review_ready";

  const loadPublishTasks = useCallback(async () => {
    if (!activeProperty) {
      setPublishTasks([]);
      return;
    }

    try {
      const tasks = await fetchPublishingTasks();
      setPublishTasks(tasks);
    } catch (error) {
      console.error(error);
      setPublishTasks([]);
    }
  }, [activeProperty]);

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

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadPublishTasks();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadPublishTasks]);

  async function handleGenerateAiFaqs() {
    try {
      setLoading(true);

      const result = await generateFaqs(
        query,
        "ai",
        contentType,
        publishPlatform,
        activeProperty?.id,
        provider,
      );

      const faqText = formatFaqResponseText(result);

      setAiFaqs(faqText);

      return {
        faqs: faqText,
        faqSetId: result.faq_set_id || null,
      };
    } catch (error) {
      console.error(error);
      setWorkflowMessage("Failed to generate AI FAQs.");

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
        publishPlatform,
        activeProperty?.id,
        provider,
      );

      if (isXiaohongshu && result.status === "retrieving") {
        if (!result.retrieval_task_id) {
          throw new Error("Xiaohongshu retrieval task was not returned.");
        }

        setWorkflowMessage("Retrieving Xiaohongshu posts...");

        for (let attempt = 0; attempt < 120; attempt += 1) {
          await wait(3000);

          const taskResult = await getRetrievalTask(result.retrieval_task_id);
          const task = taskResult.task;

          if (task.status === "completed") {
            setWorkflowMessage("");
            setPlatformQuestions(task.platform_questions || []);

            return {
              faqs: "",
              faqSetId: null,
              questions: task.platform_questions || [],
            };
          }

          if (task.status === "failed") {
            throw new Error(
              task.error_message || "Xiaohongshu retrieval failed.",
            );
          }

          setWorkflowMessage(
            `Retrieving Xiaohongshu posts... (${task.status})`,
          );
        }

        throw new Error("Xiaohongshu retrieval timed out.");
      }

      const faqText = formatFaqResponseText(result);

      setPlatformQuestions(result.platform_questions || []);

      return {
        faqs: faqText,
        faqSetId: result.faq_set_id || null,
        questions: result.platform_questions || [],
      };
    } catch (error) {
      console.error(error);
      setWorkflowMessage(
        isXiaohongshu
          ? "Failed to retrieve Xiaohongshu posts."
          : "Failed to generate platform FAQs.",
      );
      setPlatformQuestions([]);

      return {
        faqs: "",
        faqSetId: null,
        questions: [],
      };
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePackage() {
    setLoading(true);
    setWorkflowMessage("");

    try {
      const aiFaqResult = await handleGenerateAiFaqs();
      const platformFaqResult = await handleGeneratePlatformFaqs();

      const aiResult = await generateContent(
        query,
        persona,
        contentType,
        "ai",
        aiFaqResult.faqs,
        "",
        "ai_faq",
        aiFaqResult.faqSetId,
        publishPlatform,
        activeProperty?.id,
      );

      setAiGeneratedContent(aiResult.generated_content);
      setAiContentId(aiResult.content_id);
      setAiStatus("draft");
      setAiUrl("");

      const platformResult = await generateContent(
        query,
        persona,
        contentType,
        "platform",
        "",
        isXiaohongshu
          ? JSON.stringify(
              platformQuestionsForGeneration(platformFaqResult.questions),
            )
          : platformFaqResult.faqs,
        "platform_faq",
        isXiaohongshu ? null : platformFaqResult.faqSetId,
        publishPlatform,
        activeProperty?.id,
      );

      setPlatformGeneratedContent(platformResult.generated_content);
      setPlatformContentId(platformResult.content_id);
      setPlatformStatus("draft");
      setPlatformUrl("");
      await loadPublishTasks();
    } catch (error) {
      console.error(error);
      setWorkflowMessage("Failed to generate content.");
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

      await loadPublishTasks();
    } catch (error) {
      console.error(error);

      setWorkflowMessage(
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
    <Page>
      <PageHeader
        eyebrow="Workflow"
        title="Social Media Track"
        description="Manage category FAQ discovery, content generation, and publishing queue preparation for the active Property."
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

      {reviewBannerVisible && (
        <div className="rounded-lg border border-emerald-500 bg-emerald-950 px-5 py-4 font-semibold text-emerald-100">
          Human Review Required
        </div>
      )}

      {workflowMessage && (
        <div className="rounded-lg border border-amber-800 bg-amber-950/50 px-5 py-4 text-sm text-amber-200">
          {workflowMessage}
        </div>
      )}

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <ResponsiveGrid minItemWidth={180}>
          <label className="space-y-2 lg:col-span-4">
            <span className="text-sm text-zinc-400">Category</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="AI Resume Builder"
              className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition focus:border-blue-500"
            />
          </label>

          <label className="space-y-2 lg:col-span-2">
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

          <div className="lg:col-span-2">
            <LlmProviderSelector value={provider} onChange={setProvider} />
          </div>

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

          <div className="flex items-end lg:col-span-2">
            <Button
              className="w-full"
              disabled={loading || !activeProperty}
              onClick={handleGeneratePackage}
            >
              {loading ? "Generating..." : "Generate Content"}
            </Button>
          </div>
          </ResponsiveGrid>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <FaqPanel
          title="Generated AI FAQs"
          value={aiFaqs || "No AI FAQs yet."}
        />
        <PlatformQuestionPanel
          questions={platformQuestions}
          title="Retrieved Platform Questions"
          hidden={isXiaohongshu}
        />
        <PlatformPostPanel
          hidden={!isXiaohongshu}
          posts={platformQuestions}
          title="Trending Xiaohongshu Posts"
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
          platform={publishPlatform}
        />
        <ContentPanel
          body={
            platformGeneratedContent || "No platform-generated content yet."
          }
          contentId={platformContentId}
          onPublish={handlePublish}
          status={platformStatus}
          title={
            isXiaohongshu
              ? "Xiaohongshu Post-Based Content"
              : "Platform FAQ-Based Content"
          }
          url={platformUrl}
          platform={publishPlatform}
        />
      </div>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-zinc-50">
                Publish Queue
              </h2>
              <p className="mt-1 text-sm text-zinc-500">
                Property-scoped publishing tasks created from this workflow.
              </p>
            </div>
            <Button
              onClick={() => void loadPublishTasks()}
              size="sm"
              variant="outline"
            >
              Refresh
            </Button>
          </div>

          <div className="overflow-hidden rounded-lg border border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-zinc-900/70 text-xs uppercase tracking-[0.16em] text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Platform</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {publishTasks.map((task) => (
                  <tr key={task.id}>
                    <td className="px-4 py-3 font-medium text-zinc-100">
                      {task.title}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {task.platform || "Not selected"}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">
                      {formatPublishStatus(task.status)}
                    </td>
                    <td className="px-4 py-3 text-zinc-500">
                      {new Date(task.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {publishTasks.length === 0 && (
              <div className="px-4 py-6 text-sm text-zinc-500">
                No publish tasks for the current Property.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </Page>
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

type PlatformQuestionPanelProps = {
  hidden?: boolean;
  questions: PlatformQuestion[];
  title: string;
};

function PlatformQuestionPanel({
  hidden = false,
  questions,
  title,
}: PlatformQuestionPanelProps) {
  if (hidden) {
    return null;
  }

  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="flex h-[430px] flex-col p-6">
        <h2 className="mb-4 text-xl font-semibold text-zinc-50">{title}</h2>
        <div className="flex-1 overflow-y-auto rounded-xl border border-zinc-800 bg-black p-4">
          {questions.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No real platform questions retrieved yet.
            </p>
          ) : (
            <div className="space-y-3">
              {questions.map((question) => (
                <div
                  className="rounded-lg border border-zinc-800 bg-zinc-950 p-4"
                  key={question.id}
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                    <span className="rounded-full border border-zinc-700 px-2 py-1 uppercase tracking-[0.14em] text-zinc-300">
                      {formatPlatformName(question.platform)}
                    </span>
                    <span>
                      Score: {question.score ?? "n/a"}
                    </span>
                    <span>
                      {formatQuestionTimestamp(
                        question.created_at || question.discovered_at,
                      )}
                    </span>
                  </div>
                  <p className="text-sm font-medium leading-6 text-zinc-100">
                    {question.title}
                  </p>
                  {question.body && (
                    <p className="mt-2 line-clamp-3 text-sm leading-6 text-zinc-400">
                      {question.body}
                    </p>
                  )}
                  {question.url && (
                    <a
                      className="mt-3 inline-flex text-xs font-medium text-blue-400 underline hover:text-blue-300"
                      href={question.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Open source
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

type PlatformPostPanelProps = {
  hidden?: boolean;
  posts: PlatformQuestion[];
  title: string;
};

function PlatformPostPanel({
  hidden = false,
  posts,
  title,
}: PlatformPostPanelProps) {
  if (hidden) {
    return null;
  }

  return (
    <Card className="border-zinc-800 bg-zinc-950 xl:col-span-1">
      <CardContent className="flex h-[430px] flex-col p-6">
        <h2 className="mb-4 text-xl font-semibold text-zinc-50">{title}</h2>
        <div className="flex-1 overflow-y-auto rounded-xl border border-zinc-800 bg-black p-4">
          {posts.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No Xiaohongshu posts retrieved yet.
            </p>
          ) : (
            <div className="space-y-3">
              {posts.map((post) => (
                <article
                  className="rounded-lg border border-zinc-800 bg-zinc-950 p-4"
                  key={post.id}
                >
                  <h3 className="text-sm font-semibold leading-6 text-zinc-100">
                    {post.title}
                  </h3>

                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-zinc-500">
                    <span>Author: {post.author || "Unknown"}</span>
                    <span>Likes: {post.score ?? "n/a"}</span>
                    <span>
                      Published:{" "}
                      {formatQuestionTimestamp(
                        post.created_at || post.discovered_at,
                      )}
                    </span>
                  </div>

                  {post.body && (
                    <p className="mt-3 text-sm leading-6 text-zinc-400">
                      {shortPreview(post.body, 200)}
                    </p>
                  )}

                  {post.hashtags?.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {post.hashtags.slice(0, 6).map((tag) => (
                        <span
                          className="rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-300"
                          key={tag}
                        >
                          {tag.startsWith("#") ? tag : `#${tag}`}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  {post.url && (
                    <a
                      className="mt-3 inline-flex text-xs font-medium text-blue-400 underline hover:text-blue-300"
                      href={post.url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Open original post
                    </a>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function shortPreview(value: string, maxLength: number) {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength).trim()}...`;
}

function platformQuestionsForGeneration(questions: PlatformQuestion[]) {
  return questions.map((question) => ({
    title: question.title,
    author: question.author,
    score: question.score,
    created_at: question.created_at,
    discovered_at: question.discovered_at,
    hashtags: question.hashtags || [],
    body: question.body,
    url: question.url,
    engagement_metrics: question.engagement_metrics || {},
  }));
}

function formatPlatformName(platform: string) {
  return platform.replaceAll("_", " ");
}

function formatQuestionTimestamp(value: string | null) {
  if (!value) {
    return "No timestamp";
  }

  return new Date(value).toLocaleString();
}

type ContentPanelProps = {
  body: string;
  contentId: number | null;
  onPublish: (contentId: number) => void;
  platform: string;
  status: string;
  title: string;
  url: string;
};

function ContentPanel({
  body,
  contentId,
  onPublish,
  platform,
  status,
  title,
  url,
}: ContentPanelProps) {
  const preview = buildPlatformPreview(body, platform);

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
          {preview}
        </div>
      </CardContent>
    </Card>
  );
}

function buildPlatformPreview(body: string, platform: string) {
  if (platform !== "xiaohongshu") {
    return body;
  }

  try {
    const parsed = JSON.parse(body) as {
      title?: string;
      body?: string;
      hashtags?: string[];
      cta?: string;
      coverSuggestion?: string;
      imagePrompts?: string[];
    };

    return [
      parsed.title ? `标题\n${parsed.title}` : "",
      parsed.body ? `正文\n${parsed.body}` : "",
      parsed.hashtags?.length
        ? `标签\n${parsed.hashtags.join(" ")}`
        : "",
      parsed.cta ? `互动引导\n${parsed.cta}` : "",
      parsed.coverSuggestion
        ? `封面建议\n${parsed.coverSuggestion}`
        : "",
      parsed.imagePrompts?.length
        ? `图片提示\n${parsed.imagePrompts.join("\n")}`
        : "",
    ].filter(Boolean).join("\n\n");
  } catch {
    return body;
  }
}
