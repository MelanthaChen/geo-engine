import type { ReactNode } from "react";

import { Sidebar } from "@/components/Sidebar";
import { ContentContainer } from "@/components/layout/PageLayout";

type DashboardLayoutProps = {
  children: ReactNode;
};

export function AppLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <Sidebar />

      <main className="min-h-screen min-w-0 pl-64">
        <ContentContainer>{children}</ContentContainer>
      </main>
    </div>
  );
}

export const DashboardLayout = AppLayout;
