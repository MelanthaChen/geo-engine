import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent } from "../../@/components/ui/card";

const trafficData = [
  { day: "Mon", clicks: 82, impressions: 920 },
  { day: "Tue", clicks: 104, impressions: 1120 },
  { day: "Wed", clicks: 97, impressions: 1060 },
  { day: "Thu", clicks: 128, impressions: 1340 },
  { day: "Fri", clicks: 141, impressions: 1490 },
  { day: "Sat", clicks: 118, impressions: 1280 },
  { day: "Sun", clicks: 156, impressions: 1650 },
];

const visibilityData = [
  { day: "Mon", visibility: 31, citations: 2 },
  { day: "Tue", visibility: 34, citations: 3 },
  { day: "Wed", visibility: 33, citations: 2 },
  { day: "Thu", visibility: 41, citations: 5 },
  { day: "Fri", visibility: 46, citations: 6 },
  { day: "Sat", visibility: 44, citations: 5 },
  { day: "Sun", visibility: 52, citations: 7 },
];

export function DashboardCharts() {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-zinc-50">
              Website Traffic
            </h2>
            <p className="text-sm text-zinc-500">
              Clicks and impressions across tracked pages.
            </p>
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trafficData}>
                <defs>
                  <linearGradient id="clicks" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.28} />
                    <stop offset="95%" stopColor="#60a5fa" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient
                    id="impressions"
                    x1="0"
                    x2="0"
                    y1="0"
                    y2="1"
                  >
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.22} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#27272a" vertical={false} />
                <XAxis dataKey="day" stroke="#71717a" tickLine={false} />
                <YAxis stroke="#71717a" tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#09090b",
                    border: "1px solid #27272a",
                    borderRadius: 8,
                    color: "#fafafa",
                  }}
                />
                <Area
                  dataKey="impressions"
                  fill="url(#impressions)"
                  stroke="#22c55e"
                  strokeWidth={2}
                  type="monotone"
                />
                <Area
                  dataKey="clicks"
                  fill="url(#clicks)"
                  stroke="#60a5fa"
                  strokeWidth={2}
                  type="monotone"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-950">
        <CardContent className="p-6">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-zinc-50">
              Visibility Trend
            </h2>
            <p className="text-sm text-zinc-500">
              Daily visibility score compared with citation count.
            </p>
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={visibilityData}>
                <CartesianGrid stroke="#27272a" vertical={false} />
                <XAxis dataKey="day" stroke="#71717a" tickLine={false} />
                <YAxis stroke="#71717a" tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#09090b",
                    border: "1px solid #27272a",
                    borderRadius: 8,
                    color: "#fafafa",
                  }}
                />
                <Line
                  dataKey="visibility"
                  dot={false}
                  stroke="#a78bfa"
                  strokeWidth={3}
                  type="monotone"
                />
                <Line
                  dataKey="citations"
                  dot={false}
                  stroke="#f59e0b"
                  strokeWidth={3}
                  type="monotone"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
