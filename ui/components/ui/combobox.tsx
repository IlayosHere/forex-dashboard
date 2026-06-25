"use client"

import * as React from "react"
import { Combobox as ComboboxPrimitive } from "@base-ui/react/combobox"
import { ChevronDown, Check } from "lucide-react"

import { cn } from "@/lib/utils"

export interface ComboboxOption {
  value: string
  label: string
}

interface ComboboxProps {
  options: ComboboxOption[]
  value: string | null
  onChange: (value: string | null) => void
  placeholder?: string
  className?: string
  /** Shows a substring-filter input inside the popup. Defaults to on above 8 options. */
  filterable?: boolean
  "aria-label"?: string
}

/**
 * A themed replacement for native <select> with optional substring filtering
 * for long option lists. Built on @base-ui/react's Combobox primitive so
 * keyboard nav (arrows/Home/End/Escape) and type-ahead come for free.
 */
export function Combobox({ options, value, onChange, placeholder = "Select…", className, filterable, "aria-label": ariaLabel }: ComboboxProps) {
  const showFilter = filterable ?? options.length > 8
  const selected = options.find((o) => o.value === value) ?? null

  return (
    <ComboboxPrimitive.Root
      items={options}
      value={selected}
      onValueChange={(item) => onChange(item ? (item as ComboboxOption).value : null)}
      isItemEqualToValue={(a, b) => (a as ComboboxOption)?.value === (b as ComboboxOption)?.value}
      itemToStringLabel={(item) => (item as ComboboxOption)?.label ?? ""}
    >
      <ComboboxPrimitive.Trigger
        data-slot="combobox-trigger"
        aria-label={ariaLabel}
        className={cn(
          "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors flex items-center justify-between gap-2",
          className
        )}
      >
        <ComboboxPrimitive.Value>
          {(item: ComboboxOption | null) => (
            <span className={cn("truncate text-left", !item && "text-text-dim")}>
              {item ? item.label : placeholder}
            </span>
          )}
        </ComboboxPrimitive.Value>
        <ChevronDown size={14} className="text-text-muted shrink-0" />
      </ComboboxPrimitive.Trigger>

      <ComboboxPrimitive.Portal>
        <ComboboxPrimitive.Positioner className="isolate z-50" sideOffset={4} align="start">
          <ComboboxPrimitive.Popup
            data-slot="combobox-content"
            className="bg-surface-input border border-border rounded shadow-lg py-1 max-h-72 overflow-y-auto z-50 outline-none flex flex-col w-(--anchor-width)"
          >
            {showFilter && (
              <ComboboxPrimitive.Input
                placeholder="Type to filter…"
                className="bg-transparent border-b border-border text-sm text-text-primary placeholder:text-text-dim px-3 py-1.5 outline-none w-full"
              />
            )}
            <ComboboxPrimitive.Empty className="text-text-dim text-sm px-3 py-2 italic">
              No matches
            </ComboboxPrimitive.Empty>
            <ComboboxPrimitive.List>
              {(item: ComboboxOption) => (
                <ComboboxPrimitive.Item
                  key={item.value}
                  value={item}
                  className={cn(
                    "text-sm text-text-primary px-3 py-1.5 cursor-pointer flex items-center gap-2 outline-none transition-colors",
                    "data-[highlighted]:bg-border/60",
                    "data-[selected]:bg-card data-[selected]:text-bull"
                  )}
                >
                  <span className="w-3.5 shrink-0">
                    <ComboboxPrimitive.ItemIndicator>
                      <Check size={14} className="text-bull" />
                    </ComboboxPrimitive.ItemIndicator>
                  </span>
                  {item.label}
                </ComboboxPrimitive.Item>
              )}
            </ComboboxPrimitive.List>
          </ComboboxPrimitive.Popup>
        </ComboboxPrimitive.Positioner>
      </ComboboxPrimitive.Portal>
    </ComboboxPrimitive.Root>
  )
}
