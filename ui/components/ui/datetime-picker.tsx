"use client";

import * as React from "react";
import { format, parse } from "date-fns";
import { CalendarIcon } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface DateTimePickerProps {
  /** Value in "YYYY-MM-DDThh:mm" format (same as datetime-local) */
  value: string;
  onChange: (value: string) => void;
  className?: string;
  hasError?: boolean;
}

export function DateTimePicker({
  value,
  onChange,
  className,
  hasError,
}: DateTimePickerProps) {
  const [open, setOpen] = React.useState(false);

  const datePart = value?.split("T")[0] ?? "";
  const timePart = value?.split("T")[1] ?? "00:00";
  const hh = timePart.split(":")[0] ?? "00";
  const mm = timePart.split(":")[1] ?? "00";

  const selectedDate = datePart
    ? parse(datePart, "yyyy-MM-dd", new Date())
    : undefined;

  const handleDateSelect = (day: Date | undefined) => {
    if (!day) return;
    onChange(`${format(day, "yyyy-MM-dd")}T${hh}:${mm}`);
  };

  const handleHourChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!datePart) return;
    const v = Math.max(0, Math.min(23, Number(e.target.value)))
      .toString()
      .padStart(2, "0");
    onChange(`${datePart}T${v}:${mm}`);
  };

  const handleMinuteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!datePart) return;
    const v = Math.max(0, Math.min(59, Number(e.target.value)))
      .toString()
      .padStart(2, "0");
    onChange(`${datePart}T${hh}:${v}`);
  };

  const displayText = datePart ? `${datePart}  ${hh}:${mm}` : "Select date & time";

  const numInputClass =
    "w-10 h-8 bg-surface-input border border-border rounded text-sm text-text-primary text-center font-mono outline-none focus:border-bull focus:ring-1 focus:ring-bull/30 transition-colors appearance-none";

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className={cn(
          "flex h-8 w-full items-center justify-start gap-2 rounded-md border px-3 py-1 text-sm font-normal transition-colors",
          "bg-surface-input border-border text-text-primary hover:bg-surface-raised cursor-pointer",
          "focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull",
          hasError && "border-destructive",
          !value && "text-text-muted",
          className
        )}
      >
        <CalendarIcon className="size-3.5 text-text-muted" />
        <span className="font-mono text-sm">{displayText}</span>
      </PopoverTrigger>

      <PopoverContent
        align="start"
        className="w-auto bg-card border-border p-0"
      >
        <Calendar
          mode="single"
          selected={selectedDate}
          onSelect={handleDateSelect}
          className="bg-card"
        />

        <div className="flex items-center justify-center gap-2 border-t border-border px-4 py-3">
          <span className="text-xs text-text-muted mr-1">Time</span>
          <input
            type="number"
            min={0}
            max={23}
            value={hh}
            onChange={handleHourChange}
            disabled={!datePart}
            className={numInputClass}
          />
          <span className="text-text-muted font-bold font-mono">:</span>
          <input
            type="number"
            min={0}
            max={59}
            value={mm}
            onChange={handleMinuteChange}
            disabled={!datePart}
            className={numInputClass}
          />
        </div>
      </PopoverContent>
    </Popover>
  );
}
