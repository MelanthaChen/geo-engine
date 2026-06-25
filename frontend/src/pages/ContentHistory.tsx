import { type MouseEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Card, CardContent } from "../../@/components/ui/card";

import {
  deleteFaqHistory,
  deleteGeneratedContentHistory,
  fetchContentHistory,
  type HistoryItem,
} from "@/api/history";
import { useProperty } from "@/contexts/PropertyContext";

function formatPublishStatus(status: string) {
  if (status === "review_ready") {
    return "Review Ready";
  }

  return status;
}

function formatEventType(eventType?: string) {
  if (!eventType) {
    return "History";
  }

  return eventType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function groupHistoryByDate(history: HistoryItem[]) {
  return history.reduce<Record<string, HistoryItem[]>>((groups, item) => {
    const dateKey = item.created_at
      ? new Date(item.created_at).toLocaleDateString()
      : "Unknown date";

    return {
      ...groups,
      [dateKey]: [...(groups[dateKey] || []), item],
    };
  }, {});
}

export function ContentHistory() {
  const { activeProperty } = useProperty();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<HistoryItem | null>(
    null,
  );
  const [toast, setToast] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadInitialHistory() {
      if (!activeProperty) {
        setHistory([]);
        return;
      }

      try {
        const data = await fetchContentHistory();

        if (!isMounted) {
          return;
        }

        setHistory(Array.isArray(data.history) ? data.history : []);
      } catch (error) {
        console.error(error);
      }
    }

    void loadInitialHistory();

    return () => {
      isMounted = false;
    };
  }, [activeProperty]);

  function showToast(type: "success" | "error", message: string) {
    setToast({ type, message });

    setTimeout(() => {
      setToast(null);
    }, 3000);
  }

  const groupedHistory = groupHistoryByDate(history);

  async function handleDeleteHistoryItem(
    item: HistoryItem,
    event: MouseEvent<HTMLButtonElement>,
  ) {
    event.stopPropagation();

    const confirmed = window.confirm("Delete this history item?");

    if (!confirmed) {
      return;
    }

    try {
      if (item.history_item_type === "faq") {
        await deleteFaqHistory(Number(item.history_item_id));
      } else if (item.history_item_type === "generated_content") {
        await deleteGeneratedContentHistory(Number(item.history_item_id));
      } else {
        throw new Error("This history item cannot be deleted here");
      }

      const deletedIndex = history.findIndex(
        (historyItem) => historyItem.id === item.id,
      );

      const nextHistory = history.filter(
        (historyItem) => historyItem.id !== item.id,
      );

      setHistory(nextHistory);

      if (selectedHistory?.id === item.id) {
        setSelectedHistory(
          nextHistory[deletedIndex] || nextHistory[deletedIndex - 1] || null,
        );
      }

      showToast("success", "History item deleted");
    } catch (error) {
      console.error(error);
      showToast("error", "Failed to delete history item");
    }
  }

  return (
    <div className="space-y-6">
      {toast && (
        <div
          className={[
            "fixed right-6 top-6 z-50 rounded border px-4 py-2 text-sm",
            toast.type === "success"
              ? "border-emerald-700 bg-emerald-950 text-emerald-100"
              : "border-red-700 bg-red-950 text-red-100",
          ].join(" ")}
        >
          {toast.message}
        </div>
      )}

      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Archive
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Content History
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Browse persisted FAQ discovery runs and generated content artifacts.
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

      <div className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="flex h-[760px] flex-col p-6">
            <h2 className="mb-5 text-xl font-semibold text-zinc-50">
              History Items
            </h2>

            <div className="space-y-6 overflow-y-auto pr-1">
              {Object.entries(groupedHistory).map(([date, items]) => (
                <section key={date} className="space-y-3">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
                    {date}
                  </p>

                  {items.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => setSelectedHistory(item)}
                      className={[
                        "relative cursor-pointer rounded-xl border bg-black p-4 transition hover:bg-zinc-900/60",
                        selectedHistory?.id === item.id
                          ? "border-blue-500"
                          : "border-zinc-800",
                      ].join(" ")}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="pr-6 text-base font-semibold text-zinc-50">
                          {item.title}
                        </h3>

                        <div className="flex items-center gap-2">
                          <span className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300">
                            {formatEventType(item.event_type)}
                          </span>

                          {(item.history_item_type === "faq" ||
                            item.history_item_type === "generated_content") && (
                            <button
                              aria-label="Delete history item"
                              className="text-sm leading-none text-zinc-500 hover:text-red-300"
                              onClick={(event) =>
                                handleDeleteHistoryItem(item, event)
                              }
                              type="button"
                            >
                              ×
                            </button>
                          )}
                        </div>
                      </div>

                      <p className="mt-2 text-sm text-zinc-400">
                        {item.target_persona || "Property event"}
                        {" • "}
                        {item.strategy_type || item.content_type || "timeline"}
                        {" • "}
                        {item.faq_source || "property source"}
                        {" • "}
                        {item.generation_mode || "event"}
                        {" • "}
                        {formatPublishStatus(item.publish_status || "draft")}
                      </p>

                      {item.content_id && (
                        <Link
                          className="mt-3 inline-block text-sm text-blue-400 underline hover:text-blue-300"
                          to={`/content?content_id=${item.content_id}`}
                          onClick={(event) => event.stopPropagation()}
                        >
                          Related content #{item.content_id}
                        </Link>
                      )}

                      {item.event_summary && (
                        <p className="mt-3 text-sm text-zinc-500">
                          {item.event_summary}
                        </p>
                      )}

                      {(item.published_account ||
                        item.published_platform ||
                        item.published_url) && (
                        <div className="mt-3 space-y-1 text-sm text-zinc-400">
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
                              className="text-blue-400 underline"
                              href={item.published_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              Published URL
                            </a>
                          )}

                          {!item.published_url && item.preview_url && (
                            <a
                              className="text-emerald-300 underline"
                              href={item.preview_url}
                              rel="noreferrer"
                              target="_blank"
                            >
                              Review Preview
                            </a>
                          )}

                          {item.publish_status === "review_ready" && (
                            <p className="font-semibold text-emerald-300">
                              Human Review Required
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </section>
              ))}

              {history.length === 0 && (
                <p className="text-sm text-zinc-500">
                  No history events for the current property.
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-950">
          <CardContent className="flex h-[760px] flex-col p-6">
            <h2 className="mb-5 text-xl font-semibold text-zinc-50">
              Preview
            </h2>

            <div className="flex-1 overflow-y-auto whitespace-pre-wrap rounded-xl border border-zinc-800 bg-black p-5 text-sm leading-6 text-zinc-300">
              {selectedHistory?.body ||
                selectedHistory?.event_summary ||
                "Select a history item to preview its content."}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
