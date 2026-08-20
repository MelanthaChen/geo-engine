import type { ReactNode } from "react";

import { Sidebar } from "@/components/Sidebar";

type DashboardLayoutProps = {
  children: ReactNode;
};

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-black text-zinc-100">
      <Sidebar />

      <main className="min-h-screen pl-72">
        <div className="w-full px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
