export type ResearchTab = "overview" | "strategies" | "ideas" | "trials" | "journey" | "yours";

interface TabDef {
  key: ResearchTab;
  label: string;
  count?: number;
}

interface ResearchTabsProps {
  tabs: TabDef[];
  active: ResearchTab;
  onChange: (tab: ResearchTab) => void;
}

export function ResearchTabs({ tabs, active, onChange }: ResearchTabsProps) {
  return (
    <div role="tablist" className="mb-6 flex flex-wrap gap-1 border-b border-border">
      {tabs.map((tab) => {
        const selected = tab.key === active;
        return (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(tab.key)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${
              selected
                ? "border-accent-gold text-text-primary font-medium"
                : "border-transparent text-text-muted hover:text-text-primary"
            }`}
          >
            {tab.label}
            {tab.count !== undefined && <span className="ml-1.5 text-xs text-text-dim">{tab.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
