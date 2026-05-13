import { Button } from "../@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../@/components/ui/card";

import { Badge } from "../@/components/ui/badge";

function App() {
  return (
    <div className="min-h-screen bg-black text-white p-10">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-5xl font-bold">GEO Engine</h1>

            <p className="text-zinc-400 mt-2">
              Generative Engine Optimization Platform
            </p>
          </div>

          <Button>Launch Pipeline</Button>
        </div>

        {/* Dashboard Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle>Active Experiments</CardTitle>
            </CardHeader>

            <CardContent>
              <div className="text-4xl font-bold">12</div>

              <Badge className="mt-4">Running</Badge>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle>Indexed Articles</CardTitle>
            </CardHeader>

            <CardContent>
              <div className="text-4xl font-bold">248</div>

              <Badge className="mt-4">Published</Badge>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle>AI Citations</CardTitle>
            </CardHeader>

            <CardContent>
              <div className="text-4xl font-bold">73</div>

              <Badge className="mt-4">Tracking</Badge>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default App;
