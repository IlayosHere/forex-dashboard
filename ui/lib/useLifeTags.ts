"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchLifeTags } from "./api";

export function useLifeTags() {
  const [tags, setTags] = useState<string[]>([]);

  const load = useCallback(async () => {
    try {
      const data = await fetchLifeTags();
      setTags(data);
    } catch {
      // best-effort — suggestions are non-critical
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { tags, reload: load };
}
