import { BarChart3, FileText, Link2, Send } from "lucide-react";

import { Card, CardContent } from "../../@/components/ui/card";

type DashboardCardsProps = {
  generatedContent: number;
  publishedContent: number;
  trackedPrompts: number;
  citationCount: number;
};

export function DashboardCards({
  citationCount,
  generatedContent,
  publishedContent,
  trackedPrompts,
}: DashboardCardsProps) {
  const cards = [
    {
      label: "Generated Content",
      value: String(generatedContent),
      detail: "Current property",
      icon: FileText,
    },
    {
      label: "Published Content",
      value: String(publishedContent),
      detail: "Current property",
      icon: Send,
    },
    {
      label: "Tracked Prompts",
      value: String(trackedPrompts),
      detail: "Active publishing or review tasks",
      icon: BarChart3,
    },
    {
      label: "Citation Count",
      value: String(citationCount),
      detail: "Observed in citation tests",
      icon: Link2,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
