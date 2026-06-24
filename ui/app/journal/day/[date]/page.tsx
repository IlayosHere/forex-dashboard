"use client";

import { use } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { DayWorkspace } from "@/components/DayWorkspace";

import { formatDate } from "@/lib/dates";

interface DayPageProps {
  params: Promise<{ date: string }>;
}

export default function DayPage({ params }: DayPageProps) {
  const { date } = use(params);
  const searchParams = useSearchParams();
  const backHref = searchParams.get("back") ?? "/journal";
  const backLabel = searchParams.get("backLabel") ?? "Back to Journal";

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-text-primary">{formatDate(date)}</h1>
        <Link href={backHref} className="text-xs text-text-muted hover:text-text-primary">
          {backLabel}
        </Link>
      </div>
      <DayWorkspace date={date} />
    </div>
  );
}
