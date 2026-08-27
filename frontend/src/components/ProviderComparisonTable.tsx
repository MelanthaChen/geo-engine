import { comparisonProviders, type ProviderComparisonRow } from "@/types/providerComparison";

type ProviderComparisonTableProps = {
  rows: ProviderComparisonRow[];
};

export function ProviderComparisonTable({ rows }: ProviderComparisonTableProps) {
  const rowMap = new Map(rows.map((row) => [row.provider, row]));
  const mergedRows = comparisonProviders.map((provider) => ({
    ...provider,
    ...rowMap.get(provider.id),
  }));

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-zinc-800 bg-black text-xs uppercase tracking-[0.16em] text-zinc-500">
          <tr>
            <th className="px-5 py-4 font-medium">Provider</th>
            <th className="px-5 py-4 font-medium">Mentioned</th>
            <th className="px-5 py-4 font-medium">Rank</th>
            <th className="px-5 py-4 font-medium">Citation</th>
            <th className="px-5 py-4 font-medium">Latency</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {mergedRows.map((row) => {
            const isComingSoon = row.status === "coming_soon";

            return (
              <tr
                key={row.provider}
                className={isComingSoon ? "bg-zinc-950/60" : "bg-zinc-950"}
              >
                <td className="px-5 py-4 font-medium text-zinc-100">
                  <div className="flex items-center gap-2">
                    <span>{row.label}</span>
                    <span
                      className={
                        isComingSoon
                          ? "rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-500"
                          : "rounded-full border border-emerald-700 bg-emerald-950 px-2 py-0.5 text-xs text-emerald-300"
                      }
                    >
                      {isComingSoon ? "Coming Soon" : "Active"}
                    </span>
                  </div>
                </td>
                <td className="px-5 py-4 text-zinc-300">
                  {isComingSoon ? (
                    "Coming Soon"
                  ) : row.mentioned ? (
                    <span className="text-emerald-300">✓</span>
                  ) : (
                    <span className="text-zinc-500">No</span>
                  )}
                </td>
                <td className="px-5 py-4 text-zinc-300">
                  {isComingSoon ? "-" : row.rank ? `#${row.rank}` : "-"}
                </td>
                <td className="max-w-md px-5 py-4 text-zinc-400">
                  {isComingSoon ? "Support planned in a future release." : row.citation || "-"}
                </td>
                <td className="px-5 py-4 text-zinc-400">
                  {isComingSoon ? "-" : row.latency || "-"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
