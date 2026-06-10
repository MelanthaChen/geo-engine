import { useEffect, useState } from "react";

import { Button } from "../@/components/ui/button";
import { Card, CardContent } from "../@/components/ui/card";

import { generateContent } from "@/api/content";
import { generateFaqs } from "@/api/faq";
import { fetchContentHistory } from "@/api/history";
import { publishContent } from "@/api/publishing";
import { getContentStatus } from "@/api/contentStatus";
import { runCitationTest } from "@/api/citation";
import {
  fetchAccounts,
  updateAccountStage,
} from "@/api/accounts";

function App() {
  const [query, setQuery] = useState("");

  const [targetUrl, setTargetUrl] = useState("");

  const [persona, setPersona] = useState("student");

  const [contentType, setContentType] = useState("faq");

  const [loading, setLoading] = useState(false);

  const [aiGeneratedContent, setAiGeneratedContent] = useState("");

  const [platformGeneratedContent, setPlatformGeneratedContent] = useState("");

  const [aiFaqs, setAiFaqs] = useState("");

  const [platformFaqs, setPlatformFaqs] = useState("");

  const [history, setHistory] = useState<any[]>([]);

  const [selectedHistory, setSelectedHistory] = useState<any>(null);

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

  const [accounts, setAccounts] = useState<any[]>([]);

  function formatPublishStatus(status: string) {
    if (status === "draft_prepared") {
      return "Draft Prepared";
    }

    return status;
  }

  useEffect(() => {
    loadHistory();
    loadAccounts();
  }, []);

  useEffect(() => {
    const interval = setInterval(refreshStatus, 5000);

    return () => clearInterval(interval);
  }, [aiContentId, platformContentId]);

  async function handleGenerateAiContent() {
    try {
      setLoading(true);

      const result = await generateContent(
        query,
        persona,
        contentType,
        targetUrl,
        "ai",
      );

      setAiGeneratedContent(result.generated_content);

      setAiContentId(result.content_id);

      await loadHistory();
    } catch (error) {
      console.error(error);

      alert("Failed to generate AI content");
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePlatformContent() {
    try {
      setLoading(true);

      const result = await generateContent(
        query,
        persona,
        contentType,
        targetUrl,
        "platform",
      );

      setPlatformGeneratedContent(result.generated_content);

      setPlatformContentId(result.content_id);

      await loadHistory();
    } catch (error) {
      console.error(error);

      alert("Failed to generate platform content");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateAiFaqs() {
    try {
      setLoading(true);

      const result = await generateFaqs(query, "ai");

      setAiFaqs(result.faqs);
    } catch (error) {
      console.error(error);

      alert("Failed to generate AI FAQs");
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePlatformFaqs() {
    try {
      setLoading(true);

      const result = await generateFaqs(query, "platform");

      setPlatformFaqs(result.faqs);
    } catch (error) {
      console.error(error);

      alert("Failed to generate platform FAQs");
    } finally {
      setLoading(false);
    }
  }

  const handleGeneratePackage = async () => {
    setLoading(true);

    try {
      await handleGenerateAiFaqs();

      await handleGeneratePlatformFaqs();

      await handleGenerateAiContent();

      await handleGeneratePlatformContent();
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

      const result = await publishContent(contentId);

      console.log(result);
    } catch (error) {
      console.error(error);

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

  async function loadAccounts() {
    try {
      const data = await fetchAccounts();

      setAccounts(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error(error);
    }
  }

  async function handleAccountStage(
    accountId: number,
    lifecycleStage: string,
  ) {
    try {
      await updateAccountStage(accountId, lifecycleStage);

      await loadAccounts();
    } catch (error) {
      console.error(error);

      alert("Failed to update account stage");
    }
  }

  return (
    <div className="min-h-screen bg-black text-white p-10">
      <div className="max-w-7xl mx-auto space-y-8">
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
                <label className="text-sm text-zinc-400">Target Brand</label>

                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Notability"
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
                <label className="text-sm text-zinc-400">Target URL</label>

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
                  <option>faq</option>
                  <option>comparison</option>
                  <option>review</option>
                  <option>article</option>
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
                  <option>website</option>
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
                    </div>

                    <p className="text-zinc-400 text-sm mt-1">
                      {item.target_persona}
                      {" • "}
                      {item.content_type}
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
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ACCOUNT LIFECYCLE ROW */}

        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold">Account Lifecycle</h2>

              <Button size="sm" onClick={loadAccounts}>
                Refresh
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {accounts.map((account) => (
                <div
                  key={account.id}
                  className="
                    bg-zinc-950
                    border
                    border-zinc-800
                    rounded-xl
                    p-4
                    space-y-3
                  "
                >
                  <div>
                    <h3 className="font-bold truncate">{account.handle}</h3>
                    <p className="text-sm text-zinc-400">
                      {account.platform} • {account.persona}
                    </p>
                    <p className="text-xs text-zinc-500 truncate">
                      {account.account_key || `account-${account.id}`}
                    </p>
                  </div>

                  <div className="text-sm">
                    <p className="text-zinc-500">Topic</p>
                    <p>{account.assigned_topic}</p>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-sm">
                    <div className="bg-zinc-900 rounded p-2">
                      <p className="text-zinc-500">Assigned</p>
                      <p className="font-bold">
                        {account.assigned_tasks || 0}
                      </p>
                    </div>

                    <div className="bg-zinc-900 rounded p-2">
                      <p className="text-zinc-500">Published</p>
                      <p className="font-bold">
                        {account.published_tasks || 0}
                      </p>
                    </div>

                    <div className="bg-zinc-900 rounded p-2">
                      <p className="text-zinc-500">Failed</p>
                      <p className="font-bold">
                        {account.failed_tasks || 0}
                      </p>
                    </div>
                  </div>

                  <select
                    value={account.lifecycle_stage}
                    onChange={(e) =>
                      handleAccountStage(account.id, e.target.value)
                    }
                    className="
                      w-full
                      bg-zinc-900
                      border
                      border-zinc-800
                      rounded
                      p-2
                      text-sm
                    "
                  >
                    <option value="created">created</option>
                    <option value="warming">warming</option>
                    <option value="ready">ready</option>
                    <option value="publishing">publishing</option>
                    <option value="monitoring">monitoring</option>
                    <option value="paused">paused</option>
                    <option value="blocked">blocked</option>
                  </select>

                  <p className="text-xs text-zinc-500">
                    {account.is_active ? "active" : "inactive"} •{" "}
                    {account.agent_name || "no agent"} •{" "}
                    {account.health_status} • {account.last_action}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

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
              <h2 className="text-2xl font-bold mb-6">AI-Inferred FAQs</h2>

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
                Platform / Reddit FAQs
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
                    AI-Generated GEO Content
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
                        : aiStatus === "draft_prepared"
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
                    Platform-Informed GEO Content
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
                        : platformStatus === "draft_prepared"
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
