/** Shared sessionStorage key for the main /journal page's filter/mode state. */
export const JOURNAL_LIST_STATE_KEY = "journal_list_state";

interface StoredJournalListState {
  backtestMode?: boolean;
}

/** Reads whether the main journal page was last left in Backtest mode. Defaults to live (false). */
export function readJournalBacktestMode(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const saved = window.sessionStorage.getItem(JOURNAL_LIST_STATE_KEY);
    if (!saved) return false;
    return Boolean((JSON.parse(saved) as StoredJournalListState).backtestMode);
  } catch {
    return false;
  }
}
