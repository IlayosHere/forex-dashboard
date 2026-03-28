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
import { Button } from "@/components/ui/button";
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

  // Close on scroll — the popover is portaled to <body> but scroll
  // happens inside the <main> container so positioning drifts.
  React.useEffect(() => {
    if (!open) return;
    const scroller = document.querySelector("main");
    if (!scroller) return;
    const onScroll = () => setOpen(false);
    scroller.addEventListener("scroll", onScroll, { passive: true });
    return () => scroller.removeEventListener("scroll", onScroll);
  }, [open]);

  // Parse the string value into parts
  const datePart = value?.split("T")[0] || "";
  const timePart = value?.split("T")[1] || "00:00";
  const [hh, mm] = timePart.split(":").map((s) => s || "00");

  const selectedDate = datePart
    ? parse(datePart, "yyyy-MM-dd", new Date())
    : undefined;

  const handleDateSelect = (day: Date | undefined) => {
    if (!day) return;
    const dateStr = format(day, "yyyy-MM-dd");
    onChange(`${dateStr}T${hh}:${mm}`);
  };

  const handleHourChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!datePart) return;
    onChange(`${datePart}T${e.target.value}:${mm}`);
  };

  const handleMinuteChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (!datePart) return;
    onChange(`${datePart}T${hh}:${e.target.value}`);
  };

  const displayText = value
    ? `${datePart}  ${hh}:${mm}`
    : "Select date & time";

  const selectClass =
    "bg-[#1e1e1e] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-2 py-1 outline-none focus:border-[#26a69a] cursor-pointer h-8";

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className={cn(
          "flex h-8 w-full items-center justify-start gap-2 rounded-md border px-3 py-1 text-sm font-normal transition-colors",
          "bg-[#1e1e1e] border-[#2a2a2a] text-[#e0e0e0] hover:bg-[#252525] cursor-pointer",
          "focus-visible:ring-1 focus-visible:ring-offset-0 ring-[#26a69a]",
          hasError && "border-[#ef5350]",
          !value && "text-[#777777]",
          className
        )}
      >
        <CalendarIcon className="size-3.5 text-[#777777]" />
        <span className="price">{displayText}</span>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-auto bg-[#161616] border-[#2a2a2a] p-0"
      >
        <Calendar
          mode="single"
          selected={selectedDate}
          onSelect={handleDateSelect}
          className="bg-[#161616]"
        />
        <div className="flex items-center gap-2 border-t border-[#2a2a2a] px-3 py-2.5">
          <CalendarIcon className="size-3.5 text-[#777777]" />
          <span className="text-xs text-[#777777]">Time</span>
          <select
            value={hh}
            onChange={handleHourChange}
            className={selectClass}
          >
            {Array.from({ length: 24 }, (_, i) =>
              i.toString().padStart(2, "0")
            ).map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
          <span className="text-[#777777] font-bold">:</span>
          <select
            value={mm}
            onChange={handleMinuteChange}
            className={selectClass}
          >
            {Array.from({ length: 60 }, (_, i) =>
              i.toString().padStart(2, "0")
            ).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </PopoverContent>
    </Popover>
  );
}
