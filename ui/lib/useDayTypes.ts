"use client";

import { useEffect, useState } from "react";

import type { DayType } from "./types";

import { fetchDayTypes } from "./api";

export interface UseDayTypesResult {
  data: DayType[];
  loading: boolean;
}

export function useDayTypes(from: string, to: string, enabled: boolean): UseDayTypesResult {
  const [data, setData] = useState<DayType[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setData([]);
      return;
    }
    setLoading(true);
    fetchDayTypes(from, to)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [from, to, enabled]);

  return { data, loading };
}
