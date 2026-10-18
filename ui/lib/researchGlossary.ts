export interface GlossaryEntry {
  term: string;
  meaning: string;
}

export const GLOSSARY: GlossaryEntry[] = [
  { term: "Edge", meaning: "How many points of hit rate a rule gains over random entries. +5 means it wins about 5 more trades in 100." },
  { term: "Random control", meaning: "The same trades with a coin-flip direction, same days, times and bracket. A rule only counts if it beats this." },
  { term: "z-score", meaning: "How surprising a result is if the rule had no edge. Around 2 is unusual, 3 or more is rare. It grows with more trades." },
  { term: "Look", meaning: "One table or chart of results for one idea. Every look is counted, kept or not, because many looks make a lucky winner likely." },
  { term: "Promotion bar", meaning: "The z-score a new idea must beat to be taken seriously. It rises with the number of looks: sqrt(2 ln looks)." },
  { term: "Trial", meaning: "A one-shot, pre-registered test on data the rule was not built on. The project has a budget of 10 and cannot repeat one." },
  { term: "Alpha", meaning: "The chance of a false pass we allow for one trial. Smaller means stricter. The project total is 0.05, shared across trials." },
  { term: "In-sample / out of sample", meaning: "In-sample is data used to find or tune a rule. Out of sample is fresh data used once to check it." },
  { term: "Vault", meaning: "Every bar after 2026-10-09. Not looked at until a candidate passes, then used for a final one-shot check." },
  { term: "Physics gate", meaning: "A check that the trade lasts long enough to be filled on 1-minute bars. Rules that resolve in 1-3 minutes fail it." },
  { term: "Bracket", meaning: "The fixed target and stop set for a stage. The question is always: does price hit the target before the stop?" },
];
