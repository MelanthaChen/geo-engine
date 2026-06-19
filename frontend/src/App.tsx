import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { DashboardLayout } from "@/layouts/DashboardLayout";
import { CitationTests } from "@/pages/CitationTests";
import { ContentGeneration } from "@/pages/ContentGeneration";
import { ContentHistory } from "@/pages/ContentHistory";
import { Dashboard } from "@/pages/Dashboard";
import { PublishingQueue } from "@/pages/PublishingQueue";
import { Settings } from "@/pages/Settings";
import { VisibilityTracking } from "@/pages/VisibilityTracking";

function App() {
  return (
    <BrowserRouter>
      <DashboardLayout>
        <Routes>
          <Route element={<Dashboard />} path="/" />
          <Route element={<ContentGeneration />} path="/content" />
          <Route element={<PublishingQueue />} path="/publishing" />
          <Route element={<VisibilityTracking />} path="/visibility" />
          <Route element={<CitationTests />} path="/citations" />
          <Route element={<ContentHistory />} path="/history" />
          <Route element={<Settings />} path="/settings" />
          <Route element={<Navigate replace to="/" />} path="*" />
        </Routes>
      </DashboardLayout>
    </BrowserRouter>
  );
}

export default App;
