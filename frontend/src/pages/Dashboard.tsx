import { DashboardCards } from "@/components/DashboardCards";
import { DashboardCharts } from "@/components/DashboardCharts";

export function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Overview
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          GEO Dashboard
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Monitor category research, publishing throughput, visibility, and
          citation performance from one console.
        </p>
      </div>

      <DashboardCards />
      <DashboardCharts />
    </div>
  );
}
