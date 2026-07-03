"use client";

import { useRouter } from "next/navigation";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { LifeEntryCard } from "@/components/LifeEntryCard";

import type { LifeEntry } from "@/lib/types";

interface LifeDaySheetProps {
  date: string | null;
  entries: LifeEntry[];
  onClose: () => void;
}

function formatDayTitle(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00`);
  return d.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
}

export function LifeDaySheet({ date, entries, onClose }: LifeDaySheetProps) {
  const router = useRouter();

  return (
    <Sheet open={date !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className="w-[480px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{date ? formatDayTitle(date) : ""}</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-px">
          {entries.length === 0 ? (
            <p className="text-text-muted text-sm px-1 py-4">No entries for this day.</p>
          ) : (
            entries.map((entry) => (
              <LifeEntryCard
                key={entry.id}
                entry={entry}
                onClick={() => {
                  onClose();
                  router.push(`/life/${entry.id}`);
                }}
              />
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
