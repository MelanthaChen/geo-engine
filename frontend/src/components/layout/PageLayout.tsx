import type { CSSProperties, ReactNode } from "react";

import { cn } from "../../../@/lib/utils";

type PageProps = {
  children: ReactNode;
  className?: string;
};

export function Page({ children, className }: PageProps) {
  return (
    <div className={cn("min-w-0 space-y-8", className)}>{children}</div>
  );
}

export function ContentContainer({ children, className }: PageProps) {
  return (
    <div className={cn("mx-auto w-full max-w-[1760px] px-6 py-8 xl:px-8", className)}>
      {children}
    </div>
  );
}

type PageHeaderProps = {
  actions?: ReactNode;
  description: ReactNode;
  eyebrow: ReactNode;
  meta?: ReactNode;
  title: ReactNode;
};

export function PageHeader({
  actions,
  description,
  eyebrow,
  meta,
  title,
}: PageHeaderProps) {
  return (
    <header className="flex min-w-0 flex-col gap-5 border-b border-zinc-900 pb-6 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-zinc-50">{title}</h1>
        <div className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">
          {description}
        </div>
        {meta && <div className="mt-3 text-sm text-zinc-400">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}
    </header>
  );
}

type SectionProps = {
  children: ReactNode;
  className?: string;
};

export function Section({ children, className }: SectionProps) {
  return <section className={cn("min-w-0", className)}>{children}</section>;
}

type SummaryCardProps = {
  detail?: ReactNode;
  label: ReactNode;
  value: ReactNode;
};

export function SummaryGrid({ children, className }: SectionProps) {
  return (
    <div className={cn("grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-4", className)}>
      {children}
    </div>
  );
}

export function SummaryCard({ detail, label, value }: SummaryCardProps) {
  return (
    <div className="min-w-0 rounded-xl border border-zinc-800 bg-zinc-950 p-5">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">{label}</p>
      <p className="mt-2 truncate text-xl font-semibold text-zinc-50" title={typeof value === "string" ? value : undefined}>{value}</p>
      {detail && <div className="mt-1 truncate text-xs text-zinc-500">{detail}</div>}
    </div>
  );
}

type SectionHeaderProps = {
  actions?: ReactNode;
  description?: ReactNode;
  title: ReactNode;
};

export function SectionHeader({ actions, description, title }: SectionHeaderProps) {
  return (
    <div className="mb-4 flex min-w-0 flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-lg font-semibold text-zinc-50">{title}</h2>
        {description && <div className="mt-1 text-sm leading-6 text-zinc-500">{description}</div>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
}

export function EmptyState({ children, className }: SectionProps) {
  return (
    <div className={cn("flex min-h-28 items-center justify-center rounded-lg border border-dashed border-zinc-800 bg-black/40 px-6 py-8 text-center text-sm leading-6 text-zinc-500", className)}>
      {children}
    </div>
  );
}

export const fieldClassName = "h-10 w-full rounded-lg border border-zinc-800 bg-black px-3 text-sm outline-none transition focus:border-blue-500";

export function RightSidebar({ children, className }: SectionProps) {
  return <aside className={cn("min-w-0", className)}>{children}</aside>;
}

export function StickyToolbar({ children, className }: SectionProps) {
  return (
    <div
      className={cn(
        "sticky top-0 z-30 flex min-w-0 flex-wrap items-center gap-3 border-b border-zinc-800 bg-black/90 py-3 backdrop-blur",
        className,
      )}
    >
      {children}
    </div>
  );
}

type ResponsiveGridProps = {
  children: ReactNode;
  className?: string;
  gap?: "sm" | "md" | "lg";
  minItemWidth?: number;
};

const gridGaps = {
  sm: "gap-3",
  md: "gap-4",
  lg: "gap-6",
};

export function ResponsiveGrid({
  children,
  className,
  gap = "md",
  minItemWidth = 300,
}: ResponsiveGridProps) {
  const style = {
    gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${minItemWidth}px), 1fr))`,
  } satisfies CSSProperties;

  return (
    <div className={cn("grid min-w-0", gridGaps[gap], className)} style={style}>
      {children}
    </div>
  );
}

type SplitLayoutProps = {
  aside: ReactNode;
  asidePosition?: "left" | "right";
  asideWidth?: "narrow" | "wide";
  children: ReactNode;
  className?: string;
};

export function SplitLayout({
  aside,
  asidePosition = "right",
  asideWidth = "wide",
  children,
  className,
}: SplitLayoutProps) {
  const rightColumns =
    asideWidth === "narrow"
      ? "2xl:grid-cols-[minmax(0,1fr)_360px]"
      : "2xl:grid-cols-[minmax(0,1fr)_420px]";
  const leftColumns =
    asideWidth === "narrow"
      ? "2xl:grid-cols-[360px_minmax(0,1fr)]"
      : "2xl:grid-cols-[420px_minmax(0,1fr)]";

  return (
    <div
      className={cn(
        "grid min-w-0 gap-4",
        asidePosition === "right" ? rightColumns : leftColumns,
        className,
      )}
    >
      {asidePosition === "left" && <RightSidebar>{aside}</RightSidebar>}
      <div className="min-w-0">{children}</div>
      {asidePosition === "right" && <RightSidebar>{aside}</RightSidebar>}
    </div>
  );
}
