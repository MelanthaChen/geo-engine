import {
  ClipboardList,
  FileCheck2,
  FileSearch,
  FileText,
  Globe2,
  Send,
} from "lucide-react";

import { Card, CardContent } from "../../@/components/ui/card";
import { ResponsiveGrid } from "@/components/layout/PageLayout";

type DashboardCardsProps = {
  generatedContent: string;
  publishedContent: string;
  citationTests: string;
  latestAudit: string;
  latestPublish: string;
  websiteStatus: string;
};

export function DashboardCards({
  citationTests,
  generatedContent,
  latestAudit,
  latestPublish,
  publishedContent,
  websiteStatus,
}: DashboardCardsProps) {
  const cards = [
    {
      label: "Generated Content",
      value: generatedContent,
      detail: "Current property",
      icon: FileText,
    },
    {
      label: "Published Content",
      value: publishedContent,
      detail: "Current property",
      icon: Send,
    },
    {
      label: "Citation Tests",
      value: citationTests,
      detail: "Stored test records",
      icon: ClipboardList,
    },
    {
      label: "Latest Audit",
      value: latestAudit,
      detail: "Website audit",
      icon: FileSearch,
    },
    {
      label: "Latest Publish",
      value: latestPublish,
      detail: "Publishing timeline",
      icon: FileCheck2,
    },
    {
      label: "Website Status",
      value: websiteStatus,
      detail: "Active property",
      icon: Globe2,
    },
  ];

  return (
    <ResponsiveGrid minItemWidth={300}>
      {cards.map((card) => (
        <Card key={card.label} className="border-zinc-800 bg-zinc-950">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-zinc-500">{card.label}</p>
                <p className="mt-3 text-2xl font-semibold text-zinc-50">
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
    </ResponsiveGrid>
  );
}
