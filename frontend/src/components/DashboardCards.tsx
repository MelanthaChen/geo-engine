import { BarChart3, FileText, Link2, Send } from "lucide-react";

import { Card, CardContent } from "../../@/components/ui/card";

const cards = [
  {
    label: "Generated Content",
    value: "142",
    detail: "+18 this week",
    icon: FileText,
  },
  {
    label: "Published Content",
    value: "68",
    detail: "12 awaiting review",
    icon: Send,
  },
  {
    label: "Tracked Prompts",
    value: "37",
    detail: "Across 5 categories",
    icon: BarChart3,
  },
  {
    label: "Citation Count",
    value: "14",
    detail: "Observed in tests",
    icon: Link2,
  },
];

export function DashboardCards() {
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
