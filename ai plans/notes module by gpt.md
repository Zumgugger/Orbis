# Notes/Journal Module (UI Proposal)

## Goals (what the UI should optimize for)
- Capture quickly (1–2 clicks from navbar).
- Keep daily journaling frictionless (today’s entry is always one click away).
- Make retrieval easy (search + categories + simple filters).
- Support multiple note “kinds” (Instructions, Reflections, Summaries, Journal) and user-defined categories.
- Stay consistent with Orbis’ current Bootstrap + list/card UI patterns.

---

## Information Architecture

### New top-level nav item
- Add a navbar item: **Notes** (icon: `bi-journal-text` or `bi-stickies`).
- Inside Notes module, tabs (or sub-nav) for:
  1. **Notes** (all notes, all types)
  2. **Journal** (daily entries)
  3. **Weekly Review** (weekly reflections)

Rationale: keep one module entry point; let users choose the mode.

---

## Core Views

### 1) Notes Index (default)
**Route idea:** `/notes`

**Layout:** 2-column on desktop, 1-column on mobile
- Left column: list of notes (search + quick filters)
- Right column: preview / editor panel (optional; can be separate page if you want simplest implementation)

**Top bar controls**
- Search input (reuse global search style)
- Button: **New Note**

**Filters (small and minimal)**
- Type dropdown: All / Instructions / Reflections / Summaries / Journal
- Category dropdown: All + user categories
- Optional: “Pinned” toggle (only if you want later)

**List row item**
- Title
- Badges: Type, Category
- Small metadata line: updated date/time
- (Optional) snippet of first 80–120 chars

**Click behavior**
- Click a note: opens edit page or loads preview/editor.


### 2) Create/Edit Note
**Route idea:** `/notes/create`, `/notes/<id>/edit`

**Form fields**
- Title (required)
- Type (select)
- Category (select + “Manage categories” link)
- Date (optional; defaults today for Journal-type)
- Content (textarea; markdown optional later)

**Actions**
- Save
- Delete (edit only)

**UX details**
- If Type = Journal: show date selector prominently and default to today.
- If Type != Journal: date field can be collapsed/secondary.


### 3) Journal: Daily Entries
**Route idea:** `/notes/journal`

**Primary interaction**
- A “Today” card at top:
  - If today’s entry exists: show snippet + **Edit**
  - Else: show prompt + **Start today’s entry**

**Below**
- Calendar-ish list (simple): entries grouped by week or month
- Search within journal

**Prompts UI**
- Prompts displayed above the editor as small bullet questions.
- User chooses prompt set (dropdown) or “Random prompt”.


### 4) Weekly Reflection
**Route idea:** `/notes/weekly`

**Top section**
- “This week” reflection card:
  - If exists: Edit
  - Else: Start

**Weekly prompt template**
- 3–6 prompts max, e.g.:
  - What went well?
  - What was hard?
  - What will I change next week?
  - Top 3 wins

**History list**
- Past weeks listed newest-first.


### 5) Gratitude Logging
Simplest: implement as a Note Type.
- Type = **Gratitude** (or a dedicated checkbox inside Journal)

**UI suggestion (minimal)**
- In Journal editor, show a small “Gratitude” section with 3 input lines (optional).
- Stored as structured fields later; for MVP, can be embedded into content with a template.

---

## Categories UX (user-defined)

### Category management
**Route idea:** `/notes/categories`

**UI**
- List of categories
- Add category form inline (name)
- Delete category (if unused or confirm cascade behavior)

**In Create/Edit Note**
- Category select
- Next to it: small link/button “Manage” to open categories page.

---

## Note “Kinds” (Types)
Provide a default set and allow extending.

### Suggested Types
- **Instructions** (how-to, checklists)
- **Reflections** (free-form reflection)
- **Summaries** (meeting notes, book summaries)
- **Journal** (daily entry)
- (Optional) **Gratitude** (either its own type or part of Journal)

### Add new types
If you want users to add types too (not only categories):
- Mirror the categories UI with a “Types” management page.
- But if you want to keep it simple, keep types fixed for now and only let users add categories.

---

## Minimal MVP UI Flow (recommended)
If you want the least complexity first:
1. `/notes` list page (search + New)
2. `/notes/create` + `/notes/<id>/edit`
3. “Journal” is just a filtered view for Type=Journal with a Today button
4. Weekly reflection is Type=WeeklyReflection with week-start date
5. Categories as a simple admin page under notes

This gets you 90% of the UX with very little new UI surface.

---

## Data model assumptions (to support the UI)
Not implementing now, but the UI implies:
- `Note`:
  - `id`, `user_id`
  - `title`
  - `content`
  - `type` (enum/string)
  - `category_id` (nullable)
  - `entry_date` (nullable date; used for Journal/Weekly)
  - `created_at`, `updated_at`
- `NoteCategory`:
  - `id`, `user_id`, `name`

Weekly reflection: store `entry_date` as the Monday (or ISO week start).

---

## Prompts (how to present and manage)

### Prompt sets
- A few built-in prompt sets (Daily, Gratitude, Weekly)
- UI: dropdown “Prompt set” above editor

### Storage
- Store prompt sets as static lists in code at first.
- Later: allow user-defined prompt sets (a small CRUD page).

---

## UI Consistency with Orbis
- Use the same card/list-group patterns already used on Today/Tomorrow and modules.
- Keep buttons `btn-outline-*`.
- Avoid introducing complex editors initially; start with textarea.

---

## Suggested next step
If you want, I can:
- Add a placeholder Notes module (routes + templates) with the MVP screens above, wired to a simple `Note` model + migration.
