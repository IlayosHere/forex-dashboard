"use client";

import { Input } from "@/components/ui/input";
import type { UseCalculatorResult } from "@/lib/useCalculator";

interface CalculatorProps {
  direction: "BUY" | "SELL";
  calculator: UseCalculatorResult;
}

function fmt(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || isNaN(value)) return "—";
  return value.toFixed(decimals);
}

function fmtRR(rr: number | null | undefined): string {
  if (rr === null || rr === undefined || isNaN(rr)) return "—";
  return `1 : ${rr.toFixed(2)}`;
}

export function Calculator({ direction, calculator }: CalculatorProps) {
  const isBuy = direction === "BUY";
  const ringColor = isBuy ? "ring-[#26a69a]" : "ring-[#ef5350]";

  const {
    slPips, setSlPips,
    tpPips, setTpPips,
    accountBalance, setAccountBalance,
    riskPercent, setRiskPercent,
    result,
    isPending,
  } = calculator;

  return (
    <div className="space-y-4">
      {/* SL / TP inputs */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="label">SL (pips)</label>
          <Input
            type="number"
            step="0.1"
            min="0"
            value={slPips}
            onChange={(e) => setSlPips(e.target.value)}
            placeholder="e.g. 15"
            className={`bg-[#1e1e1e] border-[#2a2a2a] text-[#e0e0e0] focus-visible:ring-1 focus-visible:ring-offset-0 ${ringColor} price`}
          />
        </div>
        <div className="space-y-1">
          <label className="label">TP (pips)</label>
          <Input
            type="number"
            step="0.1"
            min="0"
            value={tpPips}
            onChange={(e) => setTpPips(e.target.value)}
            placeholder="e.g. 15"
            className={`bg-[#1e1e1e] border-[#2a2a2a] text-[#e0e0e0] focus-visible:ring-1 focus-visible:ring-offset-0 ${ringColor} price`}
          />
        </div>
      </div>

      {/* Account inputs */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="label">Account Balance</label>
          <Input
            type="number"
            step="any"
            value={accountBalance}
            onChange={(e) => setAccountBalance(e.target.value)}
            placeholder="10000"
            className={`bg-[#1e1e1e] border-[#2a2a2a] text-[#e0e0e0] focus-visible:ring-1 focus-visible:ring-offset-0 ${ringColor} price`}
          />
        </div>
        <div className="space-y-1">
          <label className="label">Risk %</label>
          <Input
            type="number"
            step="0.1"
            min="0.1"
            max="10"
            value={riskPercent}
            onChange={(e) => setRiskPercent(e.target.value)}
            placeholder="1.0"
            className={`bg-[#1e1e1e] border-[#2a2a2a] text-[#e0e0e0] focus-visible:ring-1 focus-visible:ring-offset-0 ${ringColor}`}
          />
        </div>
      </div>

      {/* Output box */}
      <div
        className={`border border-[#2a2a2a] rounded p-4 space-y-2 ${isPending ? "opacity-50" : ""}`}
        style={{ backgroundColor: "#1e1e1e" }}
      >
        <div className="flex items-end justify-between">
          <span className="label">Lot Size</span>
          <span className="lot-size" style={{ color: isBuy ? "#26a69a" : "#ef5350" }}>
            {result ? fmt(result.lot_size, 2) : "—"}
          </span>
        </div>
        <div className="border-t border-[#2a2a2a] pt-2 space-y-1.5">
          <div className="flex justify-between">
            <span className="label">Risk USD</span>
            <span className="price text-[#e0e0e0]">
              {result ? `$${fmt(result.risk_usd, 2)}` : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="label">SL Distance</span>
            <span className="price text-[#e0e0e0]">
              {result ? `${fmt(result.sl_pips, 1)} pips` : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="label">R : R</span>
            <span className="price text-[#e0e0e0]">
              {result ? fmtRR(result.rr) : "—"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
