import { useEffect, useState } from "react";

import { Card, CardContent } from "../../@/components/ui/card";

import {
  fetchCitationTests,
  type CitationTestRow,
} from "@/api/citationTests";
import { useProperty } from "@/contexts/PropertyContext";

export function CitationTests() {
  const { activeProperty } = useProperty();
  const [tests, setTests] = useState<CitationTestRow[]>([]);

  useEffect(() => {
    let isMounted = true;

    async function loadTests() {
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

    void loadTests();

    return () => {
      isMounted = false;
    };
  }, [activeProperty]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Experiments
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Citation Tests
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Inspect prompt tests, target mentions, model rank, and citation
          visibility.
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
                <th className="px-5 py-4 font-medium">Target Brand</th>
                <th className="px-5 py-4 font-medium">Mentioned</th>
                <th className="px-5 py-4 font-medium">Rank</th>
                <th className="px-5 py-4 font-medium">Model</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {tests.map((test) => (
                <tr
                  key={test.id}
                  className="transition hover:bg-zinc-900/50"
                >
                  <td className="px-5 py-4 font-medium text-zinc-100">
                    {test.query}
                  </td>
                  <td className="px-5 py-4 text-zinc-400">
                    {activeProperty?.brand_name || "No property selected"}
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={
                        test.mentioned
                          ? "text-emerald-300"
                          : "text-zinc-500"
                      }
                    >
                      {test.mentioned ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-zinc-300">
                    {test.confidence_score || "-"}
                  </td>
                  <td className="px-5 py-4 text-zinc-500">
                    {test.platform}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {tests.length === 0 && (
            <div className="border-t border-zinc-800 px-5 py-8 text-sm text-zinc-500">
              No citation tests for the current property.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
