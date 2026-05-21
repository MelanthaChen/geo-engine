import { useEffect, useState } from "react";

import { Button } from "../@/components/ui/button";
import { Card, CardContent } from "../@/components/ui/card";

import { generateContent } from "@/api/content";

import { fetchContentHistory } from "./services/history";

function App() {
  const [query, setQuery] = useState("");

  const [persona, setPersona] = useState("dog owner");

  const [contentType, setContentType] = useState("blog");

  const [loading, setLoading] = useState(false);

  const [generatedContent, setGeneratedContent] = useState("");

  const [selectedContent, setSelectedContent] = useState<any>(null);

  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    loadHistory();
  }, []);

  async function handleGenerate() {
    try {
      setLoading(true);

      const result = await generateContent(query, persona, contentType);

      setGeneratedContent(result.generated_content);

      setSelectedContent({
        body: result.generated_content,
      });

      await loadHistory();
    } catch (error) {
      console.error(error);

      alert("Failed to generate content");
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
    try {
      const data = await fetchContentHistory();

      setHistory(data);
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <div className="min-h-screen bg-black text-white p-10">
      <div className="max-w-7xl mx-auto grid grid-cols-3 gap-8">
        {/* LEFT PANEL */}

        <Card className="bg-zinc-900 border-zinc-800 col-span-1">
          <CardContent className="p-6 space-y-6">
            <div>
              <h1 className="text-4xl font-bold">GEO Engine</h1>

              <p className="text-zinc-400 mt-2">
                AI-native Generative Engine Optimization Platform
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-zinc-400">Query</label>

              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="best dog harness for puppies"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm text-zinc-400">Persona</label>

              <select
                value={persona}
                onChange={(e) => setPersona(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3"
              >
                <option>dog owner</option>

                <option>traveler</option>

                <option>student</option>

                <option>engineer</option>

                <option>parent</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm text-zinc-400">Content Type</label>

              <select
                value={contentType}
                onChange={(e) => setContentType(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3"
              >
                <option>blog</option>

                <option>faq</option>

                <option>comparison</option>

                <option>review</option>
              </select>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full"
            >
              {loading ? "Generating..." : "Generate GEO Content"}
            </Button>
          </CardContent>
        </Card>

        {/* CENTER PANEL */}

        <Card className="bg-zinc-900 border-zinc-800 col-span-1">
          <CardContent className="p-6">
            <h2 className="text-2xl font-bold mb-6">Generated Content</h2>

            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 h-[700px] overflow-y-auto whitespace-pre-wrap text-sm leading-7">
              {selectedContent
                ? selectedContent.body
                : generatedContent
                  ? generatedContent
                  : "No content generated yet."}
            </div>
          </CardContent>
        </Card>

        {/* RIGHT PANEL */}

        <Card className="bg-zinc-900 border-zinc-800 col-span-1">
          <CardContent className="p-6">
            <h2 className="text-2xl font-bold mb-6">Content History</h2>

            <div className="space-y-4 h-[700px] overflow-y-auto">
              {history.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setSelectedContent(item)}
                  className="
                   bg-zinc-950
                    border
                   border-zinc-800
                    rounded-xl
                    p-4
                    cursor-pointer
                   hover:border-zinc-600
                    transition
                  "
                >
                  <h3 className="font-bold text-lg">{item.title}</h3>

                  <p className="text-zinc-400 text-sm mt-1">
                    {item.target_persona}
                    {" • "}
                    {item.content_type}
                  </p>

                  <p className="text-zinc-500 text-xs mt-2">
                    {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default App;
