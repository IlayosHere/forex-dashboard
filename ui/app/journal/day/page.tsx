"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { nowNYDatetime } from "@/lib/dates";

/** /journal/day with no date redirects to today's date on the [date] route. */
export default function TodayDayRedirect() {
  const router = useRouter();

  useEffect(() => {
    const today = nowNYDatetime().slice(0, 10);
    router.replace(`/journal/day/${today}`);
  }, [router]);

  return null;
}
