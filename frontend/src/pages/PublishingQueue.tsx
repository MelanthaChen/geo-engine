import { useEffect, useState } from "react";

import { Card, CardContent } from "../../@/components/ui/card";

import {
  fetchPublishingTasks,
  type PublishingTask,
} from "@/api/publishingQueue";
import { useProperty } from "@/contexts/PropertyContext";

function statusBadgeClass(status: string) {
  if (status === "published") {
    return "border-emerald-700 bg-emerald-950 text-emerald-200";
  }

  if (status === "processing") {
    return "border-blue-700 bg-blue-950 text-blue-200";
  }

  if (status === "pending" || status === "review_ready") {
    return "border-amber-700 bg-amber-950 text-amber-200";
  }

  if (status === "failed") {
    return "border-red-700 bg-red-950 text-red-200";
  }

  return "border-zinc-700 bg-zinc-900 text-zinc-300";
}

function formatStatus(status: string) {
  if (status === "review_ready") {
    return "Review Ready";
  }

  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function PublishingQueue() {
  const { activeProperty } = useProperty();
  const [tasks, setTasks] = useState<PublishingTask[]>([]);

  useEffect(() => {
    let isMounted = true;

    async function loadTasks() {
      if (!activeProperty) {
        setTasks([]);
        return;
      }

      try {
        const result = await fetchPublishingTasks();

        if (isMounted) {
          setTasks(result);
        }
      } catch (error) {
        console.error(error);
        if (isMounted) {
          setTasks([]);
        }
      }
    }

    void loadTasks();

    return () => {
      isMounted = false;
    };
  }, [activeProperty]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Operations
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">
          Publishing Queue
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Review queued publishing tasks, assigned platforms, and current
          processing status.
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
          <div className="overflow-hidden rounded-lg">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-800 bg-zinc-900/70 text-xs uppercase tracking-[0.16em] text-zinc-500">
                <tr>
                  <th className="px-5 py-4 font-medium">Title</th>
                  <th className="px-5 py-4 font-medium">Platform</th>
                  <th className="px-5 py-4 font-medium">Status</th>
                  <th className="px-5 py-4 font-medium">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {tasks.map((task) => (
                  <tr
                    key={task.id}
                    className="transition hover:bg-zinc-900/50"
                  >
                    <td className="px-5 py-4 font-medium text-zinc-100">
                      {task.title}
                    </td>
                    <td className="px-5 py-4 text-zinc-400">
                      {task.platform || "Not selected"}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusBadgeClass(
                          task.status,
                        )}`}
                      >
                        {formatStatus(task.status)}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-zinc-500">
                      {new Date(task.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {tasks.length === 0 && (
              <div className="border-t border-zinc-800 px-5 py-8 text-sm text-zinc-500">
                No publishing tasks for the current property.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
