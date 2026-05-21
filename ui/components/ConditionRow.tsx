"use client";

import { Input } from "@/components/ui/input";

import type { GateCondition, ConditionOperator } from "@/lib/gatesTypes";

interface AnalyticsParam {
  name: string;
  dtype: "float" | "str" | "int" | "bool";
}

interface ConditionRowProps {
  condition: GateCondition;
  index: number;
  onChange: (c: GateCondition) => void;
  onRemove: () => void;
  params: AnalyticsParam[];
}

type DType = "float" | "str" | "int" | "bool";

const NUMERIC_OPS: ConditionOperator[] = ["gte", "lte", "between", "eq", "ne", "is_null", "not_null"];
const STRING_OPS: ConditionOperator[] = ["eq", "ne", "in", "not_in", "is_null", "not_null"];

const OP_LABELS: Record<ConditionOperator, string> = {
  eq: "=", ne: "≠", in: "in", not_in: "not in",
  gte: "≥", lte: "≤", between: "between",
  is_null: "is null", not_null: "not null",
};

function opsForDtype(dtype: DType): ConditionOperator[] {
  return dtype === "float" || dtype === "int" ? NUMERIC_OPS : STRING_OPS;
}

const SELECT_CLASSES =
  "h-8 rounded border border-border bg-surface-input text-foreground text-xs px-2 focus:outline-none focus:ring-1 focus:ring-ring";

export function ConditionRow({ condition, index, onChange, onRemove, params }: ConditionRowProps) {
  const selectedParam = params.find((p) => p.name === condition.param);
  const dtype: DType = selectedParam?.dtype ?? "float";
  const ops = opsForDtype(dtype);
  const showNoValue = condition.op === "is_null" || condition.op === "not_null";
  const showBetween = condition.op === "between";
  const showMulti = condition.op === "in" || condition.op === "not_in";

  function handleParamChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onChange({ ...condition, param: e.target.value, op: opsForDtype(dtype)[0], value: undefined, values: undefined, low: undefined, high: undefined });
  }

  function handleOpChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const op = e.target.value as ConditionOperator;
    onChange({ ...condition, op, value: undefined, values: undefined, low: undefined, high: undefined });
  }

  function handleValueChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange({ ...condition, value: e.target.value });
  }

  function handleMultiValueChange(e: React.ChangeEvent<HTMLInputElement>) {
    const parts = e.target.value.split(",").map((v) => v.trim()).filter(Boolean);
    onChange({ ...condition, values: parts });
  }

  function handleLowChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange({ ...condition, low: parseFloat(e.target.value) || 0 });
  }

  function handleHighChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange({ ...condition, high: parseFloat(e.target.value) || 0 });
  }

  return (
    <div className="flex items-center gap-2" role="group" aria-label={`Condition ${index + 1}`}>
      <select
        value={condition.param}
        onChange={handleParamChange}
        className={`${SELECT_CLASSES} w-40`}
        aria-label="Parameter"
      >
        <option value="">— param —</option>
        {params.map((p) => (
          <option key={p.name} value={p.name}>{p.name}</option>
        ))}
      </select>

      <select
        value={condition.op}
        onChange={handleOpChange}
        className={`${SELECT_CLASSES} w-28`}
        aria-label="Operator"
      >
        {ops.map((op) => (
          <option key={op} value={op}>{OP_LABELS[op]}</option>
        ))}
      </select>

      {!showNoValue && !showBetween && !showMulti && (
        <Input
          className="h-8 w-28 text-xs"
          value={String(condition.value ?? "")}
          onChange={handleValueChange}
          placeholder="value"
          aria-label="Value"
        />
      )}

      {showBetween && (
        <>
          <Input
            className="h-8 w-20 text-xs"
            type="number"
            value={String(condition.low ?? "")}
            onChange={handleLowChange}
            placeholder="low"
            aria-label="Low value"
          />
          <span className="text-xs text-muted-foreground">–</span>
          <Input
            className="h-8 w-20 text-xs"
            type="number"
            value={String(condition.high ?? "")}
            onChange={handleHighChange}
            placeholder="high"
            aria-label="High value"
          />
        </>
      )}

      {showMulti && (
        <Input
          className="h-8 w-40 text-xs"
          value={(condition.values ?? []).join(", ")}
          onChange={handleMultiValueChange}
          placeholder="a, b, c"
          aria-label="Values (comma-separated)"
        />
      )}

      <button
        type="button"
        onClick={onRemove}
        className="ml-auto text-xs text-muted-foreground hover:text-bear transition-colors px-1.5 py-1"
        aria-label={`Remove condition ${index + 1}`}
      >
        ✕
      </button>
    </div>
  );
}
