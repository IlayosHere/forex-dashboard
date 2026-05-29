"use client";

import { useState, useEffect } from "react";

const KEY = "journal:showMoney";

export function useShowMoney(): [boolean, () => void] {
  const [showMoney, setShowMoney] = useState<boolean>(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(KEY);
      if (stored !== null) setShowMoney(stored === "true");
    } catch {}
  }, []);

  function toggle() {
    setShowMoney((prev) => {
      const next = !prev;
      try { localStorage.setItem(KEY, String(next)); } catch {}
      return next;
    });
  }

  return [showMoney, toggle];
}
