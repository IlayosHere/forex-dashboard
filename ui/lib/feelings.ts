export type TradingFeeling =
  | "calm"
  | "focused"
  | "confident"
  | "anxious"
  | "impatient"
  | "fearful"
  | "greedy"
  | "distracted"
  | "revenge"
  | "tired";

export interface FeelingOption {
  value: TradingFeeling;
  label: string;
  sentiment: "positive" | "negative";
}

export const FEELING_OPTIONS: FeelingOption[] = [
  { value: "calm",        label: "Calm",        sentiment: "positive" },
  { value: "focused",     label: "Focused",     sentiment: "positive" },
  { value: "confident",   label: "Confident",   sentiment: "positive" },
  { value: "anxious",     label: "Anxious",     sentiment: "negative" },
  { value: "impatient",   label: "Impatient",   sentiment: "negative" },
  { value: "fearful",     label: "Fearful",     sentiment: "negative" },
  { value: "greedy",      label: "Greedy",      sentiment: "negative" },
  { value: "distracted",  label: "Distracted",  sentiment: "negative" },
  { value: "revenge",     label: "Revenge",     sentiment: "negative" },
  { value: "tired",       label: "Tired",       sentiment: "negative" },
];

export const FEELING_VALUES: TradingFeeling[] = FEELING_OPTIONS.map((f) => f.value);
