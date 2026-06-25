import { ClipboardList, FileQuestion, FileText, Send } from "lucide-react";

import { Card, CardContent } from "../../@/components/ui/card";

type DashboardCardsProps = {
  generatedFaqs: number;
  generatedContents: number;
  pendingPublishTasks: number;
  publishedContents: number;
  citationTestsRun: number;
};

export function DashboardCards({
  citationTestsRun,
  generatedContents,
  generatedFaqs,
  pendingPublishTasks,
  publishedContents,
}: DashboardCardsProps) {
  const cards = [
    {
      label: "Generated FAQs",
      value: String(generatedFaqs),
      detail: "Stored FAQ sets",
      icon: FileQuestion,
    },
    {
      label: "Generated Contents",
      value: String(generatedContents),
      detail: "Current property",
      icon: FileText,
    },
    {
      label: "Published Contents",
      value: String(publishedContents),
      detail: "Current property",
      icon: Send,
    },
    {
      label: "Pending Publish Tasks",
      value: String(pendingPublishTasks),
      detail: "Active publishing or review tasks",
      icon: ClipboardList,
    },
    {
      label: "Citation Tests Run",
      value: String(citationTestsRun),
      detail: "Stored test records",
      icon: ClipboardList,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      {cards.map((card) => (
        <Card key={card.label} className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-zinc-500">{card.label}</p>
                <p className="mt-3 text-3xl font-semibold text-zinc-50">
                  {card.value}
                </p>
              </div>

              <div className="rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-300">
                <card.icon className="h-5 w-5" />
              </div>
            </div>

            <p className="mt-4 text-sm text-zinc-500">{card.detail}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
