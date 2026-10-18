"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import { fetchReport } from "@/lib/researchApi";

interface ReportSheetProps {
  path: string | null;
  onClose: () => void;
}

export function ReportSheet({ path, onClose }: ReportSheetProps) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;
    setText(null);
    setError(null);
    fetchReport(path)
      .then((t) => !cancelled && setText(t))
      .catch((e: unknown) => !cancelled && setError(e instanceof Error ? e.message : "Could not load the report"));
    return () => {
      cancelled = true;
    };
  }, [path]);

  return (
    <Sheet open={path !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-[760px] max-w-[95vw]">
        <SheetHeader>
          <SheetTitle>{path?.split("/").at(-1) ?? "Report"}</SheetTitle>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-5 pb-8">
          <p className="mb-4 font-mono text-xs text-text-dim">{path}</p>
          {error && <p className="text-sm text-bear">{error}</p>}
          {!error && text === null && <p className="text-sm text-text-muted">Loading report...</p>}
          {text !== null && (
            <article className="report-body text-sm leading-relaxed text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
                {text}
              </ReactMarkdown>
            </article>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

const MARKDOWN_COMPONENTS = {
  h1: (p: React.ComponentProps<"h1">) => <h1 className="mt-4 mb-3 text-lg font-semibold" {...p} />,
  h2: (p: React.ComponentProps<"h2">) => <h2 className="mt-6 mb-2 text-base font-semibold" {...p} />,
  h3: (p: React.ComponentProps<"h3">) => <h3 className="mt-4 mb-2 text-sm font-semibold" {...p} />,
  p: (p: React.ComponentProps<"p">) => <p className="my-2" {...p} />,
  ul: (p: React.ComponentProps<"ul">) => <ul className="my-2 list-disc pl-5" {...p} />,
  ol: (p: React.ComponentProps<"ol">) => <ol className="my-2 list-decimal pl-5" {...p} />,
  code: (p: React.ComponentProps<"code">) => <code className="rounded bg-surface-input px-1 font-mono text-xs" {...p} />,
  table: (p: React.ComponentProps<"table">) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-xs" {...p} />
    </div>
  ),
  th: (p: React.ComponentProps<"th">) => <th className="border border-border px-2 py-1 text-left font-medium" {...p} />,
  td: (p: React.ComponentProps<"td">) => <td className="border border-border px-2 py-1 align-top" {...p} />,
  a: (p: React.ComponentProps<"a">) => <a className="text-breakeven underline" rel="noreferrer noopener" target="_blank" {...p} />,
};
