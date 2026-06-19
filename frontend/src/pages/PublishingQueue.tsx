import { Card, CardContent } from "../../@/components/ui/card";

const publishingTasks = [
  {
    title: "AI Resume Builders vs Traditional Resume Writing",
    platform: "Reddit",
    status: "Draft",
    created: "2026-06-19 09:40",
  },
  {
    title: "What Resume Platforms Reveal About ATS Anxiety",
    platform: "Medium",
    status: "Pending",
    created: "2026-06-19 08:15",
  },
  {
    title: "Resume Builder Alternatives for Students",
    platform: "Reddit",
    status: "Processing",
    created: "2026-06-18 17:22",
  },
  {
    title: "Common Mistakes in AI Resume Workflows",
    platform: "Blog",
    status: "Published",
    created: "2026-06-18 13:04",
  },
  {
    title: "ATS Optimization: What Actually Matters",
    platform: "Reddit",
    status: "Failed",
    created: "2026-06-17 19:31",
  },
];

function statusBadgeClass(status: string) {
  if (status === "Published") {
    return "border-emerald-700 bg-emerald-950 text-emerald-200";
  }

  if (status === "Processing") {
    return "border-blue-700 bg-blue-950 text-blue-200";
  }

  if (status === "Pending") {
    return "border-amber-700 bg-amber-950 text-amber-200";
  }

  if (status === "Failed") {
    return "border-red-700 bg-red-950 text-red-200";
  }

  return "border-zinc-700 bg-zinc-900 text-zinc-300";
}

export function PublishingQueue() {
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
                {publishingTasks.map((task) => (
                  <tr
                    key={`${task.title}-${task.created}`}
                    className="transition hover:bg-zinc-900/50"
                  >
                    <td className="px-5 py-4 font-medium text-zinc-100">
                      {task.title}
                    </td>
                    <td className="px-5 py-4 text-zinc-400">
                      {task.platform}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusBadgeClass(
                          task.status,
                        )}`}
                      >
                        {task.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-zinc-500">
                      {task.created}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
