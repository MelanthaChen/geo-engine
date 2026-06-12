import { type MouseEvent, useEffect, useState } from "react";

import { Button } from "../@/components/ui/button";
import { Card, CardContent } from "../@/components/ui/card";

import { generateContent } from "@/api/content";
import { generateFaqs } from "@/api/faq";
import {
  deleteFaqHistory,
  deleteGeneratedContentHistory,
  fetchContentHistory,
} from "@/api/history";
import { publishContent } from "@/api/publishing";
import { getContentStatus } from "@/api/contentStatus";
import { runCitationTest } from "@/api/citation";

function App() {
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

  const [query, setQuery] = useState("");

  const [targetUrl, setTargetUrl] = useState("");

  const [persona, setPersona] = useState("student");

  const [contentType, setContentType] = useState("comparison");

  const [loading, setLoading] = useState(false);

  const [aiGeneratedContent, setAiGeneratedContent] = useState("");

  const [platformGeneratedContent, setPlatformGeneratedContent] = useState("");

  const [aiFaqs, setAiFaqs] = useState("");

  const [platformFaqs, setPlatformFaqs] = useState("");

  const [history, setHistory] = useState<any[]>([]);

  const [selectedHistory, setSelectedHistory] = useState<any>(null);

  const [toast, setToast] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const [aiContentId, setAiContentId] = useState<number | null>(null);

  const [platformContentId, setPlatformContentId] = useState<number | null>(
    null,
  );

  const [aiStatus, setAiStatus] = useState("draft");

  const [platformStatus, setPlatformStatus] = useState("draft");

  const [aiUrl, setAiUrl] = useState("");

  const [platformUrl, setPlatformUrl] = useState("");

  const [publishPlatform, setPublishPlatform] = useState("reddit");

  const [citationSourceType, setCitationSourceType] = useState(
    "published_content",
  );

  const [citationResult, setCitationResult] = useState<any>(null);

  function formatPublishStatus(status: string) {
    if (status === "review_ready") {
      return "Review Ready";
    }

    return status;
  }

  const hasReviewReadyTask =
    aiStatus === "review_ready" ||
    platformStatus === "review_ready" ||
    history.some(
      (item) => item.publish_status === "review_ready"
    );

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    const interval = setInterval(refreshStatus, 5000);

    return () => clearInterval(interval);
  }, [aiContentId, platformContentId]);

  async function handleGenerateAiFaqs() {
    try {
      setLoading(true);

      const result = await generateFaqs(
        query,
        "ai",
        contentType,
        targetUrl,
      );

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

  const handleGeneratePackage = async () => {
    setLoading(true);

    try {
      const aiFaqResult = await handleGenerateAiFaqs();

      const platformFaqResult = await handleGeneratePlatformFaqs();

      const citationResult = await generateContent(
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

      setAiGeneratedContent(citationResult.generated_content);

      setAiContentId(citationResult.content_id);

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

      setPlatformGeneratedContent(
        platformResult.generated_content
      );

      setPlatformContentId(platformResult.content_id);

      await loadHistory();
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  async function handlePublish(contentId: number) {
    try {
      if (contentId === aiContentId) {
        setAiStatus("queued");
      }

      if (contentId === platformContentId) {
        setPlatformStatus("queued");
      }

      const result = await publishContent(
        contentId,
        publishPlatform,
      );

      if (result.error) {
        throw new Error(result.error);
      }

      console.log(result);
    } catch (error) {
      console.error(error);

      alert(
        error instanceof Error
          ? error.message
          : "Failed to queue content for publishing"
      );

      if (contentId === aiContentId) {
        setAiStatus("failed");
      }

      if (contentId === platformContentId) {
        setPlatformStatus("failed");
      }
    }
  }

  async function refreshStatus() {
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
  }

  async function loadHistory() {
    try {
      const data = await fetchContentHistory();

      console.log("history response:", data);

      if (Array.isArray(data)) {
        setHistory(data);
      } else if (Array.isArray(data.history)) {
        setHistory(data.history);
      } else {
        setHistory([]);
      }
    } catch (error) {
      console.error(error);
    }
  }

  function showToast(
    type: "success" | "error",
    message: string,
  ) {
    setToast({
      type,
      message,
    });

    setTimeout(() => {
      setToast(null);
    }, 3000);
  }

  async function handleDeleteHistoryItem(
    item: any,
    event: MouseEvent<HTMLButtonElement>,
  ) {
    event.stopPropagation();

    const confirmed = window.confirm("Delete this history item?");

    if (!confirmed) {
      return;
    }

    try {
      if (item.history_item_type === "faq") {
        await deleteFaqHistory(item.history_item_id);
      } else if (item.history_item_type === "generated_content") {
        await deleteGeneratedContentHistory(item.history_item_id);
      } else {
        throw new Error("This history item cannot be deleted here");
      }

      const deletedIndex = history.findIndex(
        (historyItem) => historyItem.id === item.id
      );

      const nextHistory = history.filter(
        (historyItem) => historyItem.id !== item.id
      );

      setHistory(nextHistory);

      if (selectedHistory?.id === item.id) {
        setSelectedHistory(
          nextHistory[deletedIndex] ||
            nextHistory[deletedIndex - 1] ||
            null
        );
      }

      showToast("success", "History item deleted");
    } catch (error) {
      console.error(error);
      showToast("error", "Failed to delete history item");
    }
  }

  async function handleCitationTest() {
    const contentId =
      selectedHistory?.content_id ||
      selectedHistory?.id ||
      platformContentId ||
      aiContentId;

    if (!contentId) {
      alert("Generate or select content before running a citation test");
      return;
    }

    try {
      setLoading(true);

      const result = await runCitationTest(
        Number(contentId),
        citationSourceType,
      );

      setCitationResult(result);

      await loadHistory();
    } catch (error) {
      console.error(error);

      alert("Failed to run citation test");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-black text-white p-10">
      <div className="max-w-7xl mx-auto space-y-8">
        {toast && (
          <div
            className={`
              fixed
              right-6
              top-6
              z-50
              rounded
              border
              px-4
              py-2
              text-sm
              ${
                toast.type === "success"
                  ? "border-emerald-700 bg-emerald-950 text-emerald-100"
                  : "border-red-700 bg-red-950 text-red-100"
              }
            `}
          >
            {toast.message}
          </div>
        )}

        {hasReviewReadyTask && (
          <div
            className="
              border
              border-emerald-500
              bg-emerald-950
              text-emerald-100
              rounded-lg
              px-5
              py-4
              font-bold
            "
          >
            Human Review Required
          </div>
        )}

        {/* TOP ROW */}

        <div className="grid grid-cols-2 gap-8">
          {/* CONTROL PANEL */}

          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent
              className="
      p-6
      h-[650px]
      flex
      flex-col
      gap-4
    "
            >
              <div>
                <h1 className="text-4xl font-bold">GEO Engine</h1>

                <p className="text-zinc-400 mt-2">
                  AI-native Generative Engine Optimization Platform
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-zinc-400">Category</label>

                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="AI Resume Builder"
                  className="
                    w-full
                    bg-zinc-950
                    border
                    border-zinc-800
                    rounded-lg
                    p-3
                  "
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm text-zinc-400">Website URL</label>

                <input
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="
      w-full
      bg-zinc-950
      border
      border-zinc-800
      rounded-lg
      p-3
    "
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm text-zinc-400">Persona</label>

                <select
                  value={persona}
                  onChange={(e) => setPersona(e.target.value)}
                  className="
                    w-full
                    bg-zinc-950
                    border
                    border-zinc-800
                    rounded-lg
                    p-3
                  "
                >
                  <option>student</option>
                  <option>engineering student</option>
                  <option>medical student</option>
                  <option>productivity enthusiast</option>
                  <option>researcher</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-zinc-400">Content Type</label>

                <select
                  value={contentType}
                  onChange={(e) => setContentType(e.target.value)}
                  className="
    w-full
    bg-zinc-950
    border
    border-zinc-800
    rounded-lg
    p-3
  "
                >
                  {contentTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-zinc-400">
                  Publish Platform
                </label>

                <select
                  value={publishPlatform}
                  onChange={(e) => setPublishPlatform(e.target.value)}
                  className="
      w-full
      bg-zinc-950
      border
      border-zinc-800
      rounded-lg
      p-3
    "
                >
                  <option>reddit</option>
                  <option>xiaohongshu</option>
                  <option>wordpress</option>
                  <option>github_pages</option>
                  <option>medium</option>
                </select>
              </div>

              <Button
                className="w-full"
                onClick={handleGeneratePackage}
                disabled={loading}
              >
                {loading ? "Generating GEO Package..." : "Generate GEO Package"}
              </Button>

              <div className="flex gap-4">
                <select
                  value={citationSourceType}
                  onChange={(e) => setCitationSourceType(e.target.value)}
                  className="
                    mt-4
                    w-full
                    bg-zinc-950
                    border
                    border-zinc-800
                    rounded-lg
                    p-3
                  "
                >
                  <option value="published_content">Published content</option>
                  <option value="personal_comment">Personal comment</option>
                </select>

                <Button
                  className="w-full mt-4"
                  onClick={handleCitationTest}
                  disabled={loading}
                >
                  Citation Test
                </Button>
              </div>

              {citationResult && (
                <div
                  className="
                    bg-zinc-950
                    border
                    border-zinc-800
                    rounded-lg
                    p-3
                    text-sm
                    space-y-2
                  "
                >
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Citation</span>
                    <span className="font-bold">
                      {citationResult.citation_type}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Confidence</span>
                    <span>{citationResult.confidence_score || 0}</span>
                  </div>

                  <p className="text-zinc-400 line-clamp-3">
                    {citationResult.ai_response}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* HISTORY */}

          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent
              className="
      p-6
      h-[650px]
      flex
      flex-col
    "
            >
              <h2 className="text-2xl font-bold mb-6">Content History</h2>

              <div
                className="
                space-y-4
                h-[600px]
                overflow-y-auto
              "
              >
                {history.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      console.log("Clicked");
                      console.log(JSON.stringify(item, null, 2));
                      setSelectedHistory(item);
                    }}
                    className={`
    bg-zinc-950
    border
    rounded-xl
    p-4
    cursor-pointer
    transition

    ${selectedHistory?.id === item.id ? "border-blue-500" : "border-zinc-800"}
  `}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="font-bold text-lg">{item.title}</h3>

                      <div className="flex items-center gap-2">
                        <span
                          className="
                            rounded
                            border
                            border-zinc-700
                            px-2
                            py-1
                            text-xs
                            text-zinc-300
                          "
                        >
                          {item.event_type || "content"}
                        </span>

                        {(item.history_item_type === "faq" ||
                          item.history_item_type === "generated_content") && (
                          <button
                            type="button"
                            aria-label="Delete history item"
                            onClick={(event) =>
                              handleDeleteHistoryItem(item, event)
                            }
                            className="
                              text-zinc-500
                              hover:text-red-300
                              text-sm
                              leading-none
                            "
                          >
                            ×
                          </button>
                        )}
                      </div>
                    </div>

                    <p className="text-zinc-400 text-sm mt-1">
                      {item.target_persona}
                      {" • "}
                      {item.strategy_type || item.content_type}
                      {" • "}
                      {item.faq_source || "unknown source"}
                      {" • "}
                      {item.generation_mode || "legacy"}
                      {" • "}
                      {formatPublishStatus(item.publish_status)}
                    </p>

                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                      <div className="bg-zinc-900 rounded p-2">
                        <p className="text-zinc-500">Visibility</p>
                        <p className="font-bold">
                          {item.visibility_score || 0}
                        </p>
                      </div>

                      <div className="bg-zinc-900 rounded p-2">
                        <p className="text-zinc-500">Citations</p>
                        <p className="font-bold">
                          {item.citation_count || 0}
                        </p>
                      </div>
                    </div>

                    {item.event_summary && (
                      <p className="text-zinc-500 text-sm mt-3">
                        {item.event_summary}
                      </p>
                    )}

                    {(item.published_account ||
                      item.published_platform ||
                      item.published_url) && (
                      <div className="mt-3 text-sm text-zinc-400 space-y-1">
                        <p>
                          Content{" "}
                          <span className="text-zinc-200">
                            #{item.content_id}
                          </span>
                        </p>

                        <p>
                          Published Account{" "}
                          <span className="text-zinc-200">
                            {item.published_account || "Unassigned"}
                          </span>
                        </p>

                        <p>
                          Published Platform{" "}
                          <span className="text-zinc-200">
                            {item.published_platform || "Not selected"}
                          </span>
                        </p>

                        {item.published_url && (
                          <a
                            href={item.published_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-400 underline"
                          >
                            Published URL
                          </a>
                        )}

                        {!item.published_url && item.preview_url && (
                          <a
                            href={item.preview_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-emerald-300 underline"
                          >
                            Review Preview
                          </a>
                        )}

                        {item.publish_status === "review_ready" && (
                          <p className="text-emerald-300 font-bold">
                            Human Review Required
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* FAQ ROW */}

        <div className="grid grid-cols-2 gap-8">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent
              className="
              p-6
              h-[500px]
              flex
              flex-col
            "
            >
              <h2 className="text-2xl font-bold mb-6">AI FAQs</h2>

              <div
                className="
    flex-1

    bg-zinc-950
    border
    border-zinc-800

    rounded-xl
    p-4

    overflow-y-auto
    whitespace-pre-wrap
  "
              >
                {aiFaqs || "No AI FAQs yet."}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent
              className="
      p-6
      h-[500px]
      flex
      flex-col
    "
            >
              <h2 className="text-2xl font-bold mb-6">
                Platform FAQs
              </h2>

              <div
                className="
                flex-1

               bg-zinc-950
                border
               border-zinc-800

                rounded-xl
                p-4

                overflow-y-auto
                whitespace-pre-wrap
              "
              >
                {platformFaqs || "No platform FAQs yet."}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* CONTENT ROW */}

        <div className="grid grid-cols-2 gap-8">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent
              className="
              p-6
              h-[500px]
              flex
              flex-col
            "
            >
              <div className="mb-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold">
                    AI FAQ-Based Content
                  </h2>

                  <Button
                    size="sm"
                    disabled={!aiContentId}
                    onClick={() => handlePublish(aiContentId!)}
                  >
                    Publish
                  </Button>
                </div>

                <div className="mt-3 flex items-center gap-3">
                  <span className="text-zinc-400">Status</span>

                  <span
                    className={`font-bold ${
                      aiStatus === "published"
                        ? "text-green-400"
                        : aiStatus === "review_ready"
                          ? "text-emerald-300"
                          : aiStatus === "queued"
                          ? "text-yellow-400"
                          : aiStatus === "pending"
                            ? "text-blue-400"
                            : aiStatus === "failed"
                              ? "text-red-400"
                              : "text-zinc-400"
                    }`}
                  >
                    {formatPublishStatus(aiStatus).toUpperCase()}
                  </span>

                  {aiUrl && (
                    <a
                      href={aiUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="
          text-blue-400
          hover:text-blue-300
          underline
        "
                    >
                      View Post
                    </a>
                  )}
                </div>
              </div>

              <div
                className="
    flex-1

    bg-zinc-950
    border
    border-zinc-800

    rounded-xl
    p-4

    overflow-y-auto
    whitespace-pre-wrap
  "
              >
                {selectedHistory
                  ? selectedHistory.body
                  : aiGeneratedContent || "No AI-generated content yet."}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent
              className="
      p-6
      h-[500px]
      flex
      flex-col
    "
            >
              <div className="mb-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold">
                    Platform FAQ-Based Content
                  </h2>

                  <Button
                    size="sm"
                    disabled={!platformContentId}
                    onClick={() => handlePublish(platformContentId!)}
                  >
                    Publish
                  </Button>
                </div>

                <div className="mt-3 flex items-center gap-3">
                  <span className="text-zinc-400">Status</span>

                  <span
                    className={`font-bold ${
                      platformStatus === "published"
                        ? "text-green-400"
                        : platformStatus === "review_ready"
                          ? "text-emerald-300"
                          : platformStatus === "queued"
                          ? "text-yellow-400"
                          : platformStatus === "pending"
                            ? "text-blue-400"
                            : platformStatus === "failed"
                              ? "text-red-400"
                              : "text-zinc-400"
                    }`}
                  >
                    {formatPublishStatus(platformStatus).toUpperCase()}
                  </span>

                  {platformUrl && (
                    <a
                      href={platformUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="
          text-blue-400
          hover:text-blue-300
          underline
        "
                    >
                      View Post
                    </a>
                  )}
                </div>
              </div>

              <div
                className="
    flex-1

    bg-zinc-950
    border
    border-zinc-800

    rounded-xl
    p-4

    overflow-y-auto
    whitespace-pre-wrap
  "
              >
                {selectedHistory
                  ? selectedHistory.body
                  : platformGeneratedContent ||
                    "No platform-generated content yet."}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default App;
