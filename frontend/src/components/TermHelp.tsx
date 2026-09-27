import { useState, type ReactNode } from "react";
import { Tooltip } from "radix-ui";

import { cn } from "../../@/lib/utils";
import { terminology, type TermKey, type TerminologyEntry } from "@/data/terminology";

type TermHelpProps = {
  term: TermKey;
  label?: ReactNode;
  className?: string;
  description?: string;
  detail?: string;
  example?: string;
  showLabel?: boolean;
};

export function TermHelp({
  className,
  description,
  detail,
  example,
  label,
  showLabel = true,
  term,
}: TermHelpProps) {
  const [open, setOpen] = useState(false);
  const definition: TerminologyEntry = terminology[term];
  const visibleLabel = label ?? definition.label;

  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} data-term-help={term}>
      {showLabel && <span>{visibleLabel}</span>}
      <Tooltip.Provider delayDuration={200} skipDelayDuration={100}>
        <Tooltip.Root open={open} onOpenChange={setOpen}>
          <Tooltip.Trigger asChild>
            <button
              type="button"
              aria-label={`Help for ${definition.label}`}
              className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-zinc-700 text-[10px] font-semibold leading-none text-zinc-500 outline-none transition hover:border-zinc-500 hover:text-zinc-200 focus-visible:border-blue-400 focus-visible:text-blue-300 focus-visible:ring-2 focus-visible:ring-blue-500/40"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setOpen((current) => !current);
              }}
            >
              <span aria-hidden="true">?</span>
            </button>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              className="z-[100] max-w-xs rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-left text-xs font-normal normal-case leading-5 tracking-normal text-zinc-200 shadow-xl"
              sideOffset={7}
            >
              <p>{description ?? definition.description}</p>
              {(detail ?? definition.detail) && (
                <p className="mt-1.5 text-zinc-400">{detail ?? definition.detail}</p>
              )}
              {(example ?? definition.example) && (
                <p className="mt-1.5 text-zinc-400"><span className="font-medium text-zinc-300">Example:</span> {example ?? definition.example}</p>
              )}
              <Tooltip.Arrow className="fill-zinc-700" />
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </Tooltip.Provider>
    </span>
  );
}
