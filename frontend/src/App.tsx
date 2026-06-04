import { useEffect, useState } from "react";

import { Button } from "../@/components/ui/button";
import { Card, CardContent } from "../@/components/ui/card";

import { generateContent } from "@/api/content";
import { generateFaqs } from "@/api/faq";
import { fetchContentHistory } from "@/api/history";
import { publishContent } from "@/api/publishing";
import { getContentStatus } from "@/api/contentStatus";

function App() {
  const [query, setQuery] = useState("");

  const [persona, setPersona] = useState("student");

  const [contentType, setContentType] = useState("reddit");

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

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    const interval = setInterval(refreshStatus, 5000);

    return () => clearInterval(interval);
  }, [aiContentId, platformContentId]);

  async function handleGenerateAiContent() {
    try {
      setLoading(true);

      const result = await generateContent(query, persona, contentType, "ai");

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
    alert("Citation tracking system coming next");
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
                  <option>reddit</option>
                  <option>faq</option>
                  <option>comparison</option>
                  <option>review</option>
                </select>
              </div>

              <Button
                onClick={handleGenerateAiFaqs}
                disabled={loading}
                className="w-full"
              >
                Generate AI FAQs
              </Button>

              <Button
                onClick={handleGeneratePlatformFaqs}
                disabled={loading}
                className="w-full"
              >
                Generate Platform FAQs
              </Button>

              <Button
                onClick={handleGenerateAiContent}
                disabled={loading}
                className="w-full"
              >
                Generate AI Content
              </Button>

              <Button
                onClick={handleGeneratePlatformContent}
                disabled={loading}
                className="w-full"
              >
                Generate Platform Content
              </Button>

              <div className="flex gap-4">
                <Button onClick={handleCitationTest} className="flex-1">
                  Citation Test
                </Button>
              </div>
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
                    <h3 className="font-bold text-lg">{item.title}</h3>

                    <p className="text-zinc-400 text-sm mt-1">
                      {item.target_persona}
                      {" • "}
                      {item.content_type}
                      {" • "}
                      {item.publish_status}
                    </p>
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
              h-[450px]
              flex
              flex-col
            "
            >
              <div className="mb-6">
                <h2 className="text-2xl font-bold mb-3">
                  AI-Generated GEO Content
                </h2>

                <div className="flex items-center gap-3">
                  <span className="text-zinc-400">Status:</span>

                  <span
                    className={`font-bold ${
                      aiStatus === "published"
                        ? "text-green-400"
                        : aiStatus === "queued"
                          ? "text-yellow-400"
                          : aiStatus === "pending"
                            ? "text-blue-400"
                            : aiStatus === "failed"
                              ? "text-red-400"
                              : "text-zinc-400"
                    }`}
                  >
                    {aiStatus.toUpperCase()}
                  </span>

                  <Button
                    size="sm"
                    disabled={!aiContentId}
                    onClick={() => handlePublish(aiContentId!)}
                  >
                    Publish
                  </Button>

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
                <h2 className="text-2xl font-bold mb-3">
                  Platform-Informed GEO Content
                </h2>

                <div className="flex items-center gap-3">
                  <span className="text-zinc-400">Status:</span>

                  <span
                    className={`font-bold ${
                      platformStatus === "published"
                        ? "text-green-400"
                        : platformStatus === "queued"
                          ? "text-yellow-400"
                          : platformStatus === "pending"
                            ? "text-blue-400"
                            : platformStatus === "failed"
                              ? "text-red-400"
                              : "text-zinc-400"
                    }`}
                  >
                    {platformStatus.toUpperCase()}
                  </span>

                  <Button
                    size="sm"
                    disabled={!platformContentId}
                    onClick={() => handlePublish(platformContentId!)}
                  >
                    Publish
                  </Button>

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
