import { Card, CardContent } from "../../@/components/ui/card";

import type { StrategyResult } from "@/types/experimentLab";

type StrategyComparisonTableProps = {
  results: StrategyResult[];
};

export function StrategyComparisonTable({
  results,
}: StrategyComparisonTableProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-950">
      <CardContent className="p-6">
        <h2 className="text-lg font-semibold text-zinc-50">
          Strategy Comparison
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Clean metric comparison across the original GEO paper strategies.
        </p>

        <div className="mt-5 overflow-hidden rounded-lg border border-zinc-800">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-800 bg-black text-xs uppercase tracking-[0.16em] text-zinc-500">
              <tr>
                <th className="px-4 py-3 font-medium">Strategy</th>
                <th className="px-4 py-3 font-medium">Visibility</th>
                <th className="px-4 py-3 font-medium">PAWC</th>
                <th className="px-4 py-3 font-medium">Citation Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {results.map((result) => (
                <tr key={result.strategy} className="bg-zinc-950">
                  <td className="px-4 py-3 font-medium text-zinc-100">
                    {result.label}
                  </td>
                  <td className="px-4 py-3 text-zinc-300">
                    {result.visibility.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-zinc-300">
                    {result.pawc.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-zinc-300">
                    {result.citationCount}
                  </td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr>
                  <td
                    className="px-4 py-8 text-center text-zinc-500"
                    colSpan={4}
                  >
                    Run an experiment to populate strategy results.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
