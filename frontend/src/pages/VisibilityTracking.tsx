import { useEffect, useState } from "react";
import { X } from "lucide-react";

import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";

import {
  fetchCitationTests,
  type CitationTestRow,
} from "@/api/citationTests";
import { useProperty } from "@/contexts/PropertyContext";

export function VisibilityTracking() {
  const { activeProperty } = useProperty();
  const [tests, setTests] = useState<CitationTestRow[]>([]);
  const [selectedTest, setSelectedTest] = useState<CitationTestRow | null>(
    null,
  );

  useEffect(() => {
    let isMounted = true;

    async function loadVisibilityRows() {
      if (!activeProperty) {
        setTests([]);
        return;
      }

      try {
        const result = await fetchCitationTests();

        if (isMounted) {
          setTests(result);
        }
      } catch (error) {
        console.error(error);
        if (isMounted) {
          setTests([]);
        }
      }
    }

    void loadVisibilityRows();

    return () => {
      isMounted = false;
    };
  }, [activeProperty]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Monitoring
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Visibility Tracking
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Track prompt-level visibility and inspect model responses across AI
          search surfaces.
        </p>
        {activeProperty && (
          <p className="mt-3 text-sm text-zinc-400">
            Current Property:{" "}
            <span className="text-zinc-100">{activeProperty.name}</span>
            {" • "}
            Domain:{" "}
            <span className="text-zinc-100">{activeProperty.domain}</span>
          </p>
        )}
      </div>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-800 bg-zinc-900/70 text-xs uppercase tracking-[0.16em] text-zinc-500">
              <tr>
                <th className="px-5 py-4 font-medium">Prompt</th>
                <th className="px-5 py-4 font-medium">Visibility Score</th>
                <th className="px-5 py-4 font-medium">Mention Rate</th>
                <th className="px-5 py-4 font-medium">Last Run</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {tests.map((test) => (
                <tr
                  key={test.id}
                  className="cursor-pointer transition hover:bg-zinc-900/50"
                  onClick={() => setSelectedTest(test)}
                >
                  <td className="px-5 py-4 font-medium text-zinc-100">
                    {test.query}
                  </td>
                  <td className="px-5 py-4 text-zinc-300">
                    {test.visibility_score || 0}
                  </td>
                  <td className="px-5 py-4 text-zinc-300">
                    {test.mentioned ? "100%" : "0%"}
                  </td>
                  <td className="px-5 py-4 text-zinc-500">
                    {new Date(test.tested_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {tests.length === 0 && (
            <div className="border-t border-zinc-800 px-5 py-8 text-sm text-zinc-500">
              No visibility runs for the current property.
            </div>
          )}
        </CardContent>
      </Card>

      {selectedTest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6">
          <div className="w-full max-w-3xl rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl">
            <div className="flex items-start justify-between border-b border-zinc-800 p-5">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">
                  Prompt Detail
                </p>
                <h2 className="mt-2 text-xl font-semibold text-zinc-50">
                  {selectedTest.query}
                </h2>
              </div>

              <Button
                aria-label="Close prompt detail"
                onClick={() => setSelectedTest(null)}
                size="sm"
                variant="ghost"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="p-5">
              <div className="rounded-lg border border-zinc-800 bg-black p-4">
                <h3 className="font-semibold text-zinc-100">
                  {selectedTest.platform}
                </h3>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-400">
                  {selectedTest.ai_response || "No model response stored."}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
