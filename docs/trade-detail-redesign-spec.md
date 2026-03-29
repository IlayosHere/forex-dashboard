# Trade Detail Page Redesign -- UX Architecture Specification

**Author**: UX Architect Agent
**Reads from**: existing `ui/app/journal/[id]/page.tsx`, `docs/trade-journal-ux-spec.md`, `docs/ux-spec.md`
**Hands off to**: Frontend Developer (Next.js implementation)

---

## Problems With Current Design

1. **Split-brain layout**: Two columns with independent edit states and separate save
   buttons. The left column has an "Edit" toggle with its own Save/Cancel. The right
   column has an always-editable assessment with its own "Save Changes" button. The user
   must mentally track which section is dirty and which save button belongs where.

2. **Disconnected data**: Trade identity/numbers (left) and assessment (right) feel like
   two different pages. A single trade is one thing -- the UI should treat it as one thing.

3. **Direction editing is a clickable badge**: The BUY/SELL toggle is a small colored badge
   that only becomes clickable when editing mode is active. There is no visual affordance
   indicating it is interactive, and it is easy to miss.

4. **Two save buttons**: `TradeInfoPanel` has Save/Cancel buttons inside its bordered card.
   `TradeAssessmentPanel` has a full-width "Save Changes" button at its bottom. This is
   confusing -- the user does not know if saving one section saves the other.

---

## Design Principles for the Redesign

1. **One trade, one page, one save**: All editable fields participate in a single dirty
   state. One save action at the bottom commits everything.

2. **Always-editable assessment, explicit-edit for numbers**: Assessment fields (rating,
   confidence, tags, notes, screenshot) are always editable because they are subjective
   and the user frequently revisits them. Price fields (entry, SL, TP, lot size, exit,
   direction) require an explicit edit toggle because accidental changes to numbers are
   dangerous.

3. **Single vertical flow**: No two-column split. The page reads top-to-bottom like a
   document. On wider screens, certain sections use internal multi-column grids for
   density, but the page itself is a single column.

4. **Close actions are prominent for open trades**: The close-trade workflow (enter exit
   price, pick outcome) sits at the natural decision point -- after seeing the trade
   numbers and before the assessment.

---

## Layout Structure

Maximum width: `max-w-2xl` (672px). Left-aligned within the content area (not centered),
consistent with the rest of the journal pages.

```
Back to Journal                                     (breadcrumb link)

HEADER BAR                                          (symbol, direction, strategy, time, account, status)
------------------------------------------------------------------------

TRADE NUMBERS (card)                                (entry, exit, SL, TP, lot, risk)
  [Edit pencil in top-right corner]
  When editing: direction toggle + all price inputs + inline Save/Cancel

------------------------------------------------------------------------

RESULT (card)                                       (status, P&L, R:R, duration)

------------------------------------------------------------------------

CLOSE TRADE (card, only for open trades)            (exit price input, outcome buttons)

------------------------------------------------------------------------

ASSESSMENT (card, always editable)                  (rating, confidence, tags, notes, screenshot)

------------------------------------------------------------------------

[Save Changes] button (sticky on mobile)            (single save for all dirty fields)

------------------------------------------------------------------------

Linked Signal (small link)
Delete Trade (small destructive text link)
```

---

## Section-by-Section Specification

### 1. Back Link

```
<- Back to Journal
```

- Element: `<button>` with `onClick` routing to `/journal`
- Classes: `text-xs text-text-muted hover:text-text-primary cursor-pointer transition-colors mb-4 inline-block`
- No change from current implementation.

---

### 2. Header Bar

The header is NOT inside a card. It sits directly on the page background to establish
hierarchy. It contains the trade's identity at a glance.

```
NZDUSD  ^ BUY                                  [OPEN]
fvg-impulse . 2026-03-25 16:15 UTC    Demo Account
```

**Row 1** (flex, items-center, gap-2):
- Symbol: `text-xl font-bold text-text-primary`
- Direction arrow + text: Colored badge, same styling as current
  `text-sm font-semibold px-1.5 py-0.5 rounded`
  BUY: `text-bull bg-bull/10`
  SELL: `text-bear bg-bear/10`
  This badge is NOT clickable here. Direction editing happens inside the Trade Numbers
  card when edit mode is active.
- Status badge: Pushed to the right with `ml-auto`. Uses existing `StatusBadge` component.

**Row 2** (flex, items-center, gap-2, mt-1):
- Strategy + time: `text-xs text-text-muted`
  Format: `{strategy} . {formatted open_time}`
- Account badge: Uses existing `AccountBadge` component, shown only if `account_name` exists.

**Container**: `mb-6` bottom margin to separate from first card.

---

### 3. Trade Numbers Card

A bordered card showing the core price data. Read-only by default with an edit trigger.

**Container**: `bg-card border border-border rounded p-4 space-y-3`

**Header row** (flex, justify-between, items-center):
- Left: `<span class="label">Trade Details</span>`
- Right (when NOT editing): Small edit button
  `text-[10px] uppercase tracking-wider text-text-muted hover:text-bull cursor-pointer transition-colors`
  Text: pencil character + "Edit"
- Right (when editing): Nothing (Save/Cancel are at the bottom of the card)

**Read-only layout**: Two-column grid for density on desktop, single column on mobile.

```
grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2
```

Each row is a flex justify-between pair:

```
Entry         1.08432          SL           1.08100
TP            1.08900          Lot Size     0.33
Exit          1.09100          Risk         33.2 pips
```

- Label: `.label` class
- Value: `price text-text-primary`
- Exit price shows `--` if null (open trade)
- Risk row is always read-only (calculated, never edited directly)

**Editing layout**: Same grid, but values become inputs.

When editing is activated:
1. A direction toggle appears at the top of the card (see Direction Selector section below)
2. Price fields become `<Input>` components
3. The card border changes: `border-bull/30` to indicate active editing
4. Save/Cancel buttons appear at the bottom of the card

```
[Direction toggle: BUY | SELL]

Entry         [1.08432    ]          SL           [1.08100    ]
TP            [1.08900    ]          Lot Size     [0.33       ]
Exit          [1.09100    ]

                                            [Cancel]  [Save]
```

Input styling: `h-7 bg-surface-input border-border text-text-primary text-right
focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price`

Save button: `bg-bull text-surface font-semibold` (shadcn `Button` default)
Cancel button: `variant="outline"` (shadcn)
Both: `size="sm"`

**Important**: This Save/Cancel only saves the numeric trade fields (direction, entry,
exit, SL, TP, lot size). It does NOT save assessment fields. This is an exception to the
"one save" principle because price edits are rare and consequential -- the user needs
immediate confirmation that the numbers are committed. The assessment save is separate
(see section 7).

Validation errors appear as `<p class="text-xs text-bear mt-1">` below the grid.

---

### 4. Direction Selector (inside Trade Numbers editing mode)

Replace the current "click the badge to toggle" pattern with a segmented control.

```
  DIRECTION
  [  BUY  ] [  SELL  ]
```

Implementation: Two adjacent buttons forming a toggle group.

**Container**: `flex mb-3`

**Each button**:
```
px-4 py-1.5 text-xs font-semibold uppercase tracking-wider
first:rounded-l last:rounded-r
border border-border
transition-colors
```

**Active BUY state**: `bg-bull/15 text-bull border-bull/40`
**Active SELL state**: `bg-bear/15 text-bear border-bear/40`
**Inactive state**: `bg-transparent text-text-muted border-border hover:bg-surface-raised`

The active button has a subtle filled background matching its direction color. The
inactive button is dim. Clicking switches instantly.

This toggle only appears when the Trade Numbers card is in editing mode.
When not editing, the direction is shown in the header bar as a static badge.

---

### 5. Result Card

Shows calculated trade result data. Always read-only.

**Container**: `bg-card border border-border rounded p-4 space-y-2`

**Header**: `<span class="label">Result</span>`

**Layout**: Same two-column grid as Trade Numbers for consistency on desktop.

```
grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2
```

```
Status        [WIN badge]            Duration     2h 15m
P&L           +23.4 pips (+$78.20)   R:R          1 : 1.44
```

- Status: Uses existing `StatusBadge` component
- P&L: `price font-bold` with dynamic color (`#26a69a` positive, `#ef5350` negative, `#777777` zero/null)
  USD value in parentheses: `text-xs ml-1` same color
- R:R: `price text-text-primary`
- Duration: `text-xs text-text-primary`, calculated from open_time to close_time, or "Xh Ym (running)" if open

For open trades with no result yet, P&L and R:R show `--` in muted color.

---

### 6. Close Trade Card (Open Trades Only)

Only rendered when `trade.status === "open"`. This is the decision point.

**Container**: `bg-card border border-bull/20 rounded p-4 space-y-3`
The border has a subtle bull tint to draw attention -- this is the primary action area for
open trades.

**Header**: `<span class="label">Close Trade</span>`

**Exit price input**:
```
<label class="label">Exit Price</label>
<Input type="number" step="any" ... />
```
Input styling: Same as Trade Numbers inputs but full width.

**Outcome buttons**: Two rows of two buttons in a 2x2 grid.

```
grid grid-cols-2 gap-2
```

```
[ Close as Win  ]  [ Close as Loss ]
[ Breakeven     ]  [ Cancel Trade  ]
```

- "Close as Win": `bg-bull hover:bg-bull/80 text-surface font-semibold`
  Disabled when exit price is empty. `disabled:opacity-40`
- "Close as Loss": `variant="destructive"` (shadcn, uses `bg-bear`)
  Disabled when exit price is empty.
- "Breakeven": `variant="outline"`
  Disabled when exit price is empty.
- "Cancel Trade": `variant="outline"`
  Does NOT require exit price (cancellation means the trade was not executed).

All buttons disabled while `saving` is true.

---

### 7. Assessment Card (Always Editable)

This card is always in an editable state. No edit toggle needed. Fields here are
subjective and frequently updated post-trade.

**Container**: `bg-card border border-border rounded p-4 space-y-4`

**Header**: `<span class="label">Assessment</span>`

**Rating and Confidence** (side by side on all screen sizes):

```
grid grid-cols-2 gap-4
```

```
RATING                    CONFIDENCE
[star] [star] [star] [star] [star]    [star] [star] [star] [star] [star]
```

Each sub-section:
- Label: `<label class="label mb-1 block">Rating</label>` / `Confidence`
- Stars: Existing `StarRating` component, `size="md"` (16px)
- Click same star to clear (set to null) -- existing behavior

**Tags**:
```
TAGS
[A+ setup x] [trend x] [+ add tag]
```
- Label: `<label class="label mb-1 block">Tags</label>`
- Uses existing `TagInput` component unchanged

**Notes**:
```
NOTES
+----------------------------------------------+
| Clean FVG retest, minimal wick into zone.    |
| Entered at retest of the far edge.           |
+----------------------------------------------+
```
- Label: `<label class="label mb-1 block">Notes</label>`
- `<textarea>` with:
  `w-full bg-surface-input border border-border text-text-primary rounded px-3 py-2
   text-sm outline-none focus:border-bull resize-y transition-colors`
- `rows={3}`
- Placeholder: `"Observations, lessons learned..."`

**Screenshot URL**:
```
SCREENSHOT
[https://i.imgur.com/example.png              ]
```
- Label: `<label class="label mb-1 block">Screenshot URL</label>`
- `<Input>` with placeholder `"https://..."`
- Styling: `bg-surface-input border-border text-text-primary focus-visible:ring-1
  focus-visible:ring-offset-0 ring-bull`

---

### 8. Save Button (Assessment)

A single full-width save button for all assessment fields.

```
[Save Changes]
```

- Placement: Directly below the Assessment card, with `mt-4`
- Classes: `w-full bg-bull text-surface font-semibold` (shadcn `Button`, full width)
- Disabled state: `disabled:opacity-50` when `saving` is true
- Text while saving: "Saving..."
- This button saves: rating, confidence, tags, notes, screenshot_url

**No auto-save**. The user explicitly clicks Save. Reasoning: notes are often drafted
incrementally, and auto-save on every keystroke creates unnecessary API traffic and
ambiguity about what was actually committed.

**Mobile sticky behavior**: On screens `< 640px`, the save button should be
`sticky bottom-0 z-10` with padding, so it stays visible as the user scrolls through
the assessment fields. Container gets `pb-16 sm:pb-0` to prevent content from being
hidden behind the sticky button.

Implementation for sticky:
```
<div class="sm:relative fixed bottom-0 left-0 right-0 sm:static p-4 sm:p-0 bg-surface sm:bg-transparent z-10">
  <Button ...>Save Changes</Button>
</div>
```

---

### 9. Footer Links

Below the save button, small utility links.

```
mt-6 space-y-3
```

**Linked Signal** (only if `trade.signal_id` exists):
```
<div class="border border-border rounded p-3 bg-card">
  <span class="label">Linked Signal</span>
  <button class="block text-xs text-bull hover:underline mt-1 cursor-pointer transition-colors">
    View original signal ->
  </button>
</div>
```
Clicking navigates to `/strategy/{trade.strategy}?signal={trade.signal_id}`.

**Delete Trade**:
```
<div class="pt-2">
```
- Default state: `text-xs text-text-muted hover:text-bear cursor-pointer transition-colors`
  Text: "Delete trade"
- Confirm state: Inline flex with "Are you sure?" + "Yes, delete" (destructive button) + "No" (outline button)
- Same pattern as current implementation.

---

## Edit Interaction Summary

| Field Group | Edit Mode | Save Mechanism | When |
|-------------|-----------|----------------|------|
| Trade numbers (direction, entry, exit, SL, TP, lot) | Explicit toggle ("Edit" link) | Inline Save/Cancel inside the card | Rare -- correcting data entry errors |
| Close trade (exit price + outcome) | Always available for open trades | Outcome button commits immediately | When closing a trade |
| Assessment (rating, confidence, tags, notes, screenshot) | Always editable | Single "Save Changes" button below card | Frequently -- post-trade review |

**Why not a single unified save for everything?**

Assessment fields are edited 10x more frequently than trade numbers. Forcing the user to
enter "edit mode" just to add a tag or change a rating adds friction to the most common
action. Conversely, trade numbers (entry, SL, TP) should be protected from accidental
edits because changing them retroactively affects P&L calculations. The two field groups
have different editing frequencies and different risk profiles, so they warrant different
interaction patterns.

The "two save buttons" problem from the current design was that both groups LOOKED the same
(both in bordered cards with their own save buttons) and there was no visual hierarchy
between them. In this redesign:

- Trade number editing is a rare, explicit, visually distinct mode (highlighted card border,
  inline Save/Cancel that disappears when done)
- Assessment editing is the default state (always-editable fields, one prominent save button
  at the bottom of the page)

The user's mental model: "I edit my review at the bottom and save. If I need to fix a
number, I click Edit on that card, fix it, and save it there."

---

## Responsive Behavior

### Mobile (< 640px, `sm` breakpoint)

- Page padding: `p-4`
- Max width: none (full width within content area)
- All grids collapse to single column: `grid-cols-1`
- Trade Numbers: entry, SL, TP, lot, exit, risk stack vertically
- Result: status, P&L, R:R, duration stack vertically
- Assessment rating/confidence: still side-by-side (`grid-cols-2` is maintained because
  star ratings are narrow enough)
- Save button: sticky at bottom of viewport (see section 8)

### Tablet / Small Desktop (640px - 1024px)

- Page padding: `p-6`
- Max width: `max-w-2xl`
- Trade Numbers: two-column grid (`sm:grid-cols-2`)
- Result: two-column grid (`sm:grid-cols-2`)
- Save button: static (not sticky)

### Large Desktop (> 1024px)

- Same as tablet, with more breathing room from the sidebar
- No layout changes -- `max-w-2xl` keeps the content at a comfortable reading width

---

## Component Architecture

### Files to Modify

1. **`ui/app/journal/[id]/page.tsx`** -- Page orchestrator. Rewrite to use the new
   single-column layout and unified state management. This file fetches data, manages
   save handlers, and composes child components.

2. **`ui/components/TradeInfoPanel.tsx`** -- Rename or rewrite as `TradeNumbersCard.tsx`.
   Remove the header (symbol/direction/strategy) from this component -- that now lives
   in the page. This component is just the bordered card with price rows and edit mode.

3. **`ui/components/TradeResultPanel.tsx`** -- Minor update: change to two-column grid
   layout internally. No structural changes.

4. **`ui/components/TradeCloseActions.tsx`** -- No structural changes, just verify it
   works standalone in the new layout position.

5. **`ui/components/TradeAssessmentPanel.tsx`** -- Remove the "Save Changes" button from
   inside this component. The save button is now external (in the page). This component
   becomes a pure form that receives values and change handlers.

### New Component

6. **`ui/components/DirectionToggle.tsx`** -- The segmented BUY/SELL control. Small
   enough to be its own component since it will also be useful in the New Trade form.

```typescript
interface DirectionToggleProps {
  value: "BUY" | "SELL";
  onChange: (v: "BUY" | "SELL") => void;
}
```

### Components Unchanged

- `StatusBadge.tsx` -- used as-is
- `StarRating.tsx` -- used as-is
- `TagInput.tsx` -- used as-is
- `AccountBadge.tsx` -- used as-is

---

## State Management in the Page

The page (`[id]/page.tsx`) manages two separate dirty states:

### Trade Numbers State

```typescript
const [editing, setEditing] = useState(false);
// Local state inside TradeNumbersCard, committed on Save
```

When the user clicks "Edit" on the Trade Numbers card, the card enters edit mode with
local state. On Save, it calls `onSave(fields)` which the page handles by calling
`updateTrade()`. On Cancel, local state resets.

### Assessment State

```typescript
// Managed via useReducer in the page, same as current
const [editable, dispatch] = useReducer(editableReducer, INITIAL_EDITABLE);
```

Fields: `tags`, `notes`, `rating`, `confidence`, `screenshotUrl`. Always editable,
committed on "Save Changes" click.

### Close Trade State

```typescript
// exitPrice managed in the page via reducer, same as current
```

On outcome button click, calls `closeTrade(outcome)` which commits immediately.

---

## Accessibility Notes

- Direction toggle: `role="radiogroup"` with `role="radio"` on each button,
  `aria-checked` on the active one, keyboard navigation with arrow keys
- Star ratings: Already have click-to-clear behavior. Ensure `aria-label` describes
  the current value (e.g., "Rating: 3 out of 5 stars")
- Save button: `aria-busy="true"` while saving
- Delete confirmation: Focus should move to the "Yes, delete" button when confirmation
  appears
- All form inputs must have associated `<label>` elements (already done via the
  `.label` styled elements, but ensure `htmlFor` attributes are present)

---

## Visual Hierarchy Summary

From top to bottom, the visual weight decreases:

1. **Header** -- Largest text (xl), bold, colored direction badge, status badge
2. **Trade Numbers** -- Card with price data, high information density
3. **Result** -- Card with outcomes, colored P&L draws the eye
4. **Close Trade** -- Card with subtle bull-tinted border (open trades only), action buttons
5. **Assessment** -- Card with subjective fields, lower visual weight
6. **Save Button** -- Full width, bull-colored, clear call to action
7. **Footer links** -- Smallest text, muted, utility actions

This ordering matches the user's reading pattern: "What trade is this? What are the
numbers? What happened? (Can I close it?) What do I think about it? Save."

---

## What the Frontend Developer Must NOT Do

- Do not add toast notifications for save/delete -- use inline feedback (existing pattern)
- Do not auto-save assessment fields on change -- explicit save only
- Do not add animations or transitions between edit/read modes beyond the border color change
- Do not create a separate mobile layout component -- responsive CSS handles it
- Do not center the page content -- it stays left-aligned within the content area
- Do not deviate from the existing color palette -- no new colors
- Do not add undo/redo -- save is explicit, delete has confirmation
