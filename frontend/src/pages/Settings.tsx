import { Card, CardContent } from "../../@/components/ui/card";

const sections = [
  {
    title: "Backend Configuration",
    fields: ["API Base URL", "Environment", "Health Check Path"],
  },
  {
    title: "Publishing Accounts",
    fields: ["Account ID", "Agent Name", "Default Platform"],
  },
  {
    title: "Google Search Console",
    fields: ["Property URL", "Service Account", "Import Schedule"],
  },
  {
    title: "Reddit Session",
    fields: ["State File", "Review Mode", "Browser Channel"],
  },
  {
    title: "OpenAI Configuration",
    fields: ["Model", "Temperature", "Request Timeout"],
  },
];

export function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-zinc-500">
          Admin
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">Settings</h1>
        <p className="mt-2 max-w-3xl text-sm text-zinc-500">
          Configure integrations and runtime defaults for local research and
          publishing workflows.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {sections.map((section) => (
          <Card key={section.title} className="border-zinc-800 bg-zinc-950">
            <CardContent className="space-y-4 p-6">
              <div>
                <h2 className="text-lg font-semibold text-zinc-50">
                  {section.title}
                </h2>
                <p className="mt-1 text-sm text-zinc-500">
                  Placeholder configuration fields.
                </p>
              </div>

              <div className="space-y-3">
                {section.fields.map((field) => (
                  <label key={field} className="block space-y-2">
                    <span className="text-sm text-zinc-400">{field}</span>
                    <input
                      className="w-full rounded-lg border border-zinc-800 bg-black p-3 text-sm outline-none transition placeholder:text-zinc-700 focus:border-blue-500"
                      placeholder={`Enter ${field.toLowerCase()}`}
                    />
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
