"use client";

import { useState, useEffect, useCallback } from "react";

import { ConditionRow } from "@/components/ConditionRow";
import { GatePreviewPanel } from "@/components/GatePreviewPanel";
import { Button } from "@/components/ui/button";
import { fetchAnalyticsParameters } from "@/lib/analyticsApi";

import type { GateCondition, GatePreviewResponse } from "@/lib/gatesTypes";

interface AnalyticsParam {
  name: string;
  dtype: "float" | "str" | "int" | "bool";
}

interface ConditionBuilderProps {
  conditions: GateCondition[];
  onChange: (conditions: GateCondition[]) => void;
  strategy: string;
  preview?: GatePreviewResponse | null;
  previewLoading?: boolean;
}

const DEFAULT_CONDITION: GateCondition = { param: "", op: "gte" };

export function ConditionBuilder({
  conditions,
  onChange,
  strategy,
  preview,
  previewLoading,
}: ConditionBuilderProps) {
  const [params, setParams] = useState<AnalyticsParam[]>([]);
  const [paramsError, setParamsError] = useState<string | null>(null);

  const loadParams = useCallback(async () => {
    try {
      const data = await fetchAnalyticsParameters(strategy);
      setParams(data.items as AnalyticsParam[]);
    } catch (e) {
      setParamsError(e instanceof Error ? e.message : "Failed to load parameters");
    }
  }, [strategy]);

  useEffect(() => { void loadParams(); }, [loadParams]);

  function handleAdd() {
    onChange([...conditions, { ...DEFAULT_CONDITION }]);
  }

  function handleChange(index: number, updated: GateCondition) {
    onChange(conditions.map((c, i) => (i === index ? updated : c)));
  }

  function handleRemove(index: number) {
    onChange(conditions.filter((_, i) => i !== index));
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {conditions.length === 0 && (
          <p className="text-xs text-muted-foreground py-2">
            No conditions yet. Add one to start filtering signals.
          </p>
        )}

        {paramsError && (
          <p className="text-xs text-bear">{paramsError}</p>
        )}

        {conditions.map((cond, i) => (
          <ConditionRow
            key={i}
            condition={cond}
            index={i}
            onChange={(updated) => handleChange(i, updated)}
            onRemove={() => handleRemove(i)}
            params={params}
          />
        ))}
      </div>

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        className="text-xs h-7"
      >
        + Add Condition
      </Button>

      {previewLoading && (
        <p className="text-xs text-muted-foreground animate-pulse">Computing preview...</p>
      )}

      {preview && !previewLoading && (
        <GatePreviewPanel preview={preview} conditions={conditions} />
      )}
    </div>
  );
}
