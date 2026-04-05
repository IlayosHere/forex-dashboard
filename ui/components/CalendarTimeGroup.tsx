import { CalendarEventRow } from "@/components/CalendarEventRow";

import type { CalendarContext, CalendarEvent } from "@/lib/types";

interface CalendarTimeGroupProps {
  timeLabel: string;
  events: CalendarEvent[];
  context: CalendarContext;
  currentTime: Date;
}

export function CalendarTimeGroup({ timeLabel, events, context, currentTime }: CalendarTimeGroupProps) {
  if (events.length === 0) return null;

  return (
    <div>
      <div
        className="text-[10px] uppercase tracking-widest text-text-dim px-3 py-1 border-b border-border"
        role="rowgroup"
        aria-label={`Events at ${timeLabel}`}
      >
        {timeLabel}
      </div>
      {events.map((event) => (
        <CalendarEventRow
          key={event.id}
          event={event}
          context={context}
          isPast={new Date(event.datetime_utc) < currentTime}
        />
      ))}
    </div>
  );
}
