import { useEffect, useState } from "react";

import {
  fetchPropertyMetrics,
  type PropertyMetrics,
} from "@/api/properties";
import {
  fetchContentHistory,
  type HistoryItem,
} from "@/api/history";
import {
  fetchCitationTests,
  type CitationTestRow,
} from "@/api/citationTests";
import { Card, CardContent } from "../../@/components/ui/card";
import { DashboardCards } from "@/components/DashboardCards";
import { useProperty } from "@/contexts/PropertyContext";

export function Dashboard() {
  const { activeProperty } = useProperty();
  const [metrics, setMetrics] = useState<PropertyMetrics | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [citationTests, setCitationTests] = useState<CitationTestRow[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadMetrics() {
      if (!activeProperty) {
        setMetrics(null);
        return;
      }

      try {
        const [metricResult, historyResult, citationResult] =
          await Promise.all([
            fetchPropertyMetrics(activeProperty.id),
            fetchContentHistory(),
            fetchCitationTests(),
          ]);

        if (isMounted) {
          setMetrics(metricResult);
          setHistory(historyResult.history || []);
          setCitationTests(citationResult);
          setLastUpdated(new Date().toLocaleString());
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
          Monitor category research, publishing throughput, and citation
          testing from one console.
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
        citationTests={formatMetric(citationTests.length)}
        generatedContent={formatMetric(metrics?.generated_content)}
        latestAudit="No data yet."
        latestPublish={latestPublishLabel(history)}
        publishedContent={formatMetric(metrics?.published_content)}
        websiteStatus={activeProperty ? "Active" : "No data yet."}
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold text-zinc-50">
              Current Property
            </h2>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <MetricLine
                label="Property"
                value={activeProperty?.name || "No property selected"}
              />
              <MetricLine
                label="Domain"
                value={activeProperty?.domain || "No active domain"}
              />
              <MetricLine
                label="Generated Contents"
                value={String(metrics?.generated_content ?? 0)}
              />
              <MetricLine
                label="Published Contents"
                value={String(metrics?.published_content ?? 0)}
              />
              <MetricLine
                label="Citation Tests Run"
                value={formatMetric(citationTests.length)}
              />
              <MetricLine
                label="Last Updated"
                value={lastUpdated || "Not loaded yet"}
              />
            </div>

            <div className="mt-6 rounded-lg border border-zinc-800 bg-black p-4 text-sm text-zinc-500">
              TODO: traffic clicks and impressions require a backend Google
              Search Console endpoint. Fake traffic charts have been removed.
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold text-zinc-50">
              Recent History
            </h2>
            <div className="mt-4 space-y-3">
              {history.slice(0, 6).map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg border border-zinc-800 bg-black p-3"
                >
                  <p className="text-sm font-medium text-zinc-100">
                    {item.event_summary || item.title || "History event"}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {formatEventLabel(item.event_type)}
                    {item.created_at
                      ? ` • ${new Date(item.created_at).toLocaleString()}`
                      : ""}
                  </p>
                </div>
              ))}

              {history.length === 0 && (
                <p className="text-sm text-zinc-500">
                  No history events for the current property.
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetricLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black p-4">
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="mt-2 text-base font-semibold text-zinc-100">{value}</p>
    </div>
  );
}

function formatEventLabel(eventType?: string) {
  if (!eventType) {
    return "History";
  }

  return eventType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatMetric(value?: number | null) {
  if (!value) {
    return "No data yet.";
  }

  return String(value);
}

function latestPublishLabel(history: HistoryItem[]) {
  const publishEvent = history.find((item) =>
    ["publish_requested", "published", "publish_failed", "review_ready"]
      .includes(item.event_type || ""),
  );

  if (!publishEvent) {
    return "No data yet.";
  }

  return publishEvent.created_at
    ? new Date(publishEvent.created_at).toLocaleDateString()
    : "Available";
}
