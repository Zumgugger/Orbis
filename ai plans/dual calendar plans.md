# Dual Calendar Integration Plan

## Overview

Integrate Orbis with two Google Calendars:
1. **Private Calendar** — Full todo details, bidirectional sync
2. **Shared Calendar** — Simplified "blocks" for family visibility, one-way sync (Orbis → Google)

---

## User Requirements

### Core Concept
- Private calendar contains all todo details (titles, descriptions, times)
- Shared calendar shows simplified "blocks" (e.g., "Work", "Concert", "Schulferien")
- Family subscribes to the shared calendar to see availability without clutter
- User subscribes to family calendars in their private calendar

### Sync Direction
| Calendar | Direction | What Syncs |
|----------|-----------|------------|
| Private | Bidirectional | Full todo details, completion status |
| Shared | One-way (Orbis → Google) | Time blocks with generic titles |

### Todo Types
| Type | Orbis | Private Calendar | Shared Calendar |
|------|-------|------------------|-----------------|
| No date/time | ✅ | ❌ | ❌ |
| Date only (no time) | ✅ | All-day event | All-day block (if marked) |
| Date + time + duration | ✅ | Timed event | Timed block (if marked) |

---

## Block Fusion Rules

Blocks in the shared calendar are calculated by fusing individual todos according to these priority rules:

### Priority 1: Work Hours Fusion (7:00–17:30)
All todos between 7:00 and 17:30 fuse into ONE block, regardless of gaps.

**Title construction**: Combine unique shared titles.
- Example: Todos with "Work" + "Music" → Block titled "Work, Music"

### Priority 2: Gap ≤ 1 Hour Fusion
Outside work hours, if gap between consecutive todos is ≤ 1 hour, fuse them.

**Title construction**: Same as Priority 1.

### Priority 3: Gap > 1 Hour = Separate Blocks
If gap exceeds 1 hour (outside work hours), create separate blocks.

### Multi-day Events
Events spanning multiple days (e.g., "Schulferien") create ONE all-day event with date range, not multiple single-day events.

---

## Deletion & Update Behavior

| Action | Private Calendar | Shared Calendar |
|--------|------------------|-----------------|
| Todo deleted | Event deleted | Recalculate blocks, update/delete as needed |
| Todo time changed | Event updated | Recalculate blocks, update accordingly |
| Todo completed | Event marked with ✓ | Recalculate blocks (completed todos excluded?) |

**Note**: User accepts responsibility for communicating with family if shared blocks change.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER'S GOOGLE ACCOUNT                        │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │   Primary Calendar   │    │   Shared Calendar    │           │
│  │   (private details)  │    │   (family blocks)    │           │
│  │                      │    │                      │           │
│  │  • Buy groceries     │    │  • Work (9-17:30)    │──────────►│ Family subscribes
│  │  • Meeting @10:00    │    │  • Concert (20-23)   │           │
│  │  • Dentist @14:00    │    │  • Schulferien       │           │
│  │  • Concert @20:00    │    │    (Dec 20 - Jan 3)  │           │
│  └──────────────────────┘    └──────────────────────┘           │
│           ▲                            ▲                         │
│           │ bidirectional              │ one-way (Orbis → Google)│
│           │                            │                         │
└───────────┼────────────────────────────┼─────────────────────────┘
            │                            │
            └──────────┬─────────────────┘
                       │
              ┌────────▼────────┐
              │      ORBIS      │
              │                 │
              │  Todos with:    │
              │  • title        │
              │  • due_date     │
              │  • due_time     │
              │  • shared_title │
              │  • sync_shared  │
              └─────────────────┘
```

---

## Technical Decisions

### Calendar Setup (Recommended)
Use **one Google account** with two calendars (not two separate accounts):
- Simpler OAuth (one token for both calendars)
- Easier token management
- Same API calls, just different calendar IDs

### OAuth
Existing OAuth scope (`calendar.events`) works for any calendar the user has write access to. No scope changes needed.

### Calendar ID Configuration
Store shared calendar ID in User model (settings page) rather than environment variable for multi-user support.

---

## Data Model Changes

### Todo Model Additions
```python
# New fields
sync_to_shared = db.Column(db.Boolean, default=False)
shared_title = db.Column(db.String(50), nullable=True)  # "Work", "Concert", etc.
shared_event_id = db.Column(db.String(255), nullable=True)  # Links to shared calendar event
```

### New Model: SharedTitle
```python
class SharedTitle(db.Model):
    """Frequently used titles for shared calendar blocks"""
    __tablename__ = "shared_titles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(50), nullable=False)
    is_default_work_hours = db.Column(db.Boolean, default=False)  # Auto-select for 7-17:30
    position = db.Column(db.Integer, default=0)  # For ordering in dropdown

    user = db.relationship("User", backref="shared_titles")
```

### User Model Addition
```python
shared_calendar_id = db.Column(db.String(255), nullable=True)  # Secondary calendar ID
```

---

## Block Calculation Algorithm

```python
def calculate_shared_blocks(todos_for_day):
    """
    Calculate shared calendar blocks from todos.
    Returns list of Block objects to sync to shared calendar.
    """
    # Filter todos that have times and sync_to_shared=True
    timed_todos = [t for t in todos_for_day if t.due_time and t.sync_to_shared]

    if not timed_todos:
        return []

    # Sort by start time
    timed_todos.sort(key=lambda t: t.due_time)

    blocks = []
    current_block = None

    for todo in timed_todos:
        start = todo.due_time
        end = calculate_end_time(todo)  # end_time or start + duration

        if current_block is None:
            current_block = Block(start, end, titles={todo.shared_title})
        else:
            gap_minutes = minutes_between(current_block.end, start)

            # Check if within work hours (7:00-17:30)
            is_work_hours = (
                time(7, 0) <= start <= time(17, 30) and
                time(7, 0) <= current_block.start <= time(17, 30)
            )

            # FUSION RULES
            if is_work_hours:
                # Priority 1: Always fuse within work hours
                current_block.end = max(current_block.end, end)
                current_block.titles.add(todo.shared_title)
            elif gap_minutes <= 60:
                # Priority 2: Fuse if gap <= 1 hour
                current_block.end = max(current_block.end, end)
                current_block.titles.add(todo.shared_title)
            else:
                # Priority 3: Gap > 1 hour, new block
                blocks.append(current_block)
                current_block = Block(start, end, titles={todo.shared_title})

    if current_block:
        blocks.append(current_block)

    # Format titles: {"Work", "Music"} → "Work, Music"
    for block in blocks:
        block.title = ", ".join(sorted(block.titles))

    return blocks
```

---

## UI Changes

### Todo Form
- Checkbox: "Show in shared calendar" (sync_to_shared)
- Dropdown: Shared title selection (from SharedTitle table)
- Text input: Custom title option (if not in dropdown)

### Defaults
- For todos with time between 7:00–17:30: default sync_to_shared=True, shared_title="Work"
- For todos outside work hours: default sync_to_shared=False (user opts in)

### Settings Page
- Input: Shared calendar ID (paste from Google Calendar settings)
- CRUD: Manage frequently used shared titles
- Set default work hours title

### Flash Messages
Clear feedback for sync operations:
- "✓ Synced to private calendar" with link
- "✓ Synced to shared calendar" with link
- "⚠ Failed to sync to shared calendar: [error]" with retry option

---

## Implementation Plan

### Phase 1: Foundation (Database & Models)
1. Create migration: Add `shared_calendar_id` to User model
2. Create migration: Add `sync_to_shared`, `shared_title`, `shared_event_id` to Todo model
3. Create migration: Add SharedTitle model
4. Create SharedTitle CRUD endpoints
5. Add settings UI for shared calendar ID configuration
6. Seed default shared titles for existing users

### Phase 2: Core Sync Feature
7. Refactor CalendarService to accept calendar_id parameter (not hardcoded `primary`)
8. Implement `create_event_in_calendar(calendar_id, ...)` method
9. Implement `update_event_in_calendar(calendar_id, ...)` method
10. Implement `delete_event_in_calendar(calendar_id, ...)` method
11. Implement block calculation algorithm
12. Implement block sync logic (compare existing blocks, create/update/delete as needed)

### Phase 3: Todo Integration
13. Modify todo create to sync to both calendars
14. Modify todo update to sync to both calendars
15. Modify todo delete to recalculate and sync blocks
16. Modify todo complete/uncomplete to handle both calendars
17. Add flash messages with calendar links

### Phase 4: UI
18. Add sync_to_shared checkbox to todo form
19. Add shared_title dropdown to todo form
20. Implement default selection logic (work hours → auto-check + "Work")
21. Add shared titles management to settings page

### Phase 5: Day Visualization (Future)
22. Implement calendarList API to discover all accessible calendars
23. Let user select which calendars to display in Orbis
24. Build day timeline view with todos + external calendar events
25. Color-code by calendar source

---

## Pre-Implementation Checklist

Before coding, user needs to:

1. **Create shared calendar** in Google account: ✅ DONE
   - Google Calendar → Settings → Add calendar → Create new calendar
   - Name: "Family Blocks" or "Shared Schedule"
   - Calendar ID: `3f9c5be70ad712f969525b2f893cf7e465c5b56d82abf59d0574616c8934b3f0@group.calendar.google.com`
   - Share with family members ("See all event details" access)

2. **Confirm default shared titles**: ✅ CONFIRMED
   - Work (default for 7:00–17:30, also selectable outside those times)
   - Sitzung
   - Musik
   - Konzert
   - + Custom title option (free text input)

3. **Decide on settings storage**: ✅ Settings page (multi-user support)

4. **OAuth Setup**: ✅ DONE
   - Project: glass-world-209910
   - User: markus.gugger@gmail.com
   - Calendar API enabled

---

## Risk Mitigation

### Race Conditions
When updating both calendars, if one fails:
- Show clear flash message indicating which succeeded/failed
- Store partial state (e.g., private synced, shared failed)
- Provide retry mechanism

### Token Expiry
- Both calendars use same OAuth token
- Existing token refresh logic applies
- If token invalid, redirect to re-auth (existing behavior)

### Block Recalculation Performance
- Only recalculate blocks for affected day(s)
- Cache block state to minimize API calls
- Consider background job for bulk operations

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| One account or two? | One account, two calendars |
| Block fusion rules? | Work hours always fuse; otherwise fuse if gap ≤ 1 hour |
| Multi-day events? | One event spanning date range |
| View family calendars in Orbis? | Phase 5 (later) — user can see them in Google Calendar meanwhile |
| Completed todos in blocks? | **Resolved**: See rules below |

### Completed Todos in Shared Blocks — Rules

| Scenario | Behavior |
|----------|----------|
| Block has **started** (current time ≥ block start) | Keep completed todos in block calculation |
| Block is in the **future** (current time < block start) | Remove completed todos, recalculate blocks |

**Rationale**: If a block has started, family already sees it — removing it mid-block would be confusing. But if you complete something scheduled for tomorrow, it should disappear from the shared calendar since it's no longer happening.

---

## Version History

- **2026-01-01**: Initial plan created from discussion
