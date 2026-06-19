import { useEffect, useState } from "react";

import {
  fetchPropertyMetrics,
  type PropertyMetrics,
} from "@/api/properties";
import { DashboardCards } from "@/components/DashboardCards";
import { DashboardCharts } from "@/components/DashboardCharts";
import { useProperty } from "@/contexts/PropertyContext";

export function Dashboard() {
  const { activeProperty } = useProperty();
  const [metrics, setMetrics] = useState<PropertyMetrics | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadMetrics() {
      if (!activeProperty) {
        setMetrics(null);
        return;
      }

      try {
        const result = await fetchPropertyMetrics(activeProperty.id);

        if (isMounted) {
          setMetrics(result);
        }
      } catch (error) {
        console.error(error);
      }
    }

    void loadMetrics();

    return () => {
      isMounted = false;
    };
  }, [activeProperty]);

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

      <DashboardCards
        citationCount={metrics?.citation_count ?? 0}
        generatedContent={metrics?.generated_content ?? 0}
        publishedContent={metrics?.published_content ?? 0}
        trackedPrompts={metrics?.tracked_prompts ?? 0}
      />
      <DashboardCharts
        clicks={metrics?.clicks ?? 0}
        impressions={metrics?.impressions ?? 0}
        visibilityScore={metrics?.visibility_score ?? 0}
        citationCount={metrics?.citation_count ?? 0}
      />
    </div>
  );
}
