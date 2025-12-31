# Orbis Feature Improvements Plan

**Date:** December 30, 2025
**Purpose:** Prioritized improvements for existing features and new feature additions

---

## Part 1: Improvements to Existing Features (Priority 1-10)

### Priority 3: Daily Streak Recovery & History
**Current:** Streaks break with no recovery option, no history view
**Improvement:**
- "Streak freeze" feature (1-3 per month) to preserve streaks
- Visual streak calendar showing completion history
- Weekly/monthly completion rate statistics
- Allow marking dailies complete for past dates (within reason)

### Priority 4: Habit Insights & Trends
**Current:** Simple count and progress bar
**Improvement:**
- Line charts showing habit count over time
- Weekly/monthly trend analysis
- Best streak tracking per habit
- Correlation insights (e.g., "You exercise more on Mondays")
- Heat map visualization like GitHub contributions

### Priority 5: Goal Progress Visualization
**Current:** Basic milestone checkboxes with percentage
**Improvement:**
- Timeline view with milestone deadlines
- Gantt-style visualization for multi-milestone goals
- Sub-milestones (nested milestones)
- Link todos to specific milestones
- Goal categories and filtering

### Priority 6: Enhanced Search & Filtering
**Current:** Basic search across entities
**Improvement:**
- Advanced filters (date range, priority, status, category)
- Saved search/filter presets
- Full-text search in descriptions and notes
- Search within Ideas notes and mindmaps
- Tag-based filtering across all entities

### Priority 7: Ideas Module Enhancement
**Current:** Basic ideas with notes, mindmaps, and file attachments
**Improvement:**
- Rich text editor for notes (WYSIWYG)
- Better mindmap editor with drag-and-drop nodes
- Link ideas to goals/todos for actionability
- Idea templates for common types (project, business, creative)
- Export ideas to PDF/Markdown

### Priority 8: Shopping List Categories & Smart Features
**Current:** Simple text-based shopping lists
**Improvement:**
- Structured items with quantity, unit, category
- Auto-categorize items (groceries, household, etc.)
- Recurring/favorite items for quick add
- Price tracking (optional)
- Share shopping lists (future multi-user)

### Priority 9: Mobile-Optimized Quick Actions
**Current:** Works on mobile but not optimized for quick input
**Improvement:**
- Floating action button (FAB) for quick add
- Swipe gestures (swipe to complete, swipe to delete)
- Voice input for quick todo/idea capture
- Offline mode with sync when back online
- Home screen widget/PWA improvements

### Priority 10: Notification & Reminder System
**Current:** No notifications or reminders
**Improvement:**
- Browser push notifications for due todos
- Daily digest email (morning preview, evening summary)
- Reminder times configurable per todo/daily
- "Don't break the chain" streak reminders
- Calendar event reminders integration

---

## Part 2: New Features/Modules to Add (Priority 1-20)

### Priority 1: Weekly/Monthly Review Dashboard 📊
**Description:** Comprehensive view of productivity over time
- Weekly summary: completed vs planned tasks
- Monthly goal progress overview
- Habit consistency scores
- Streak achievements
- Time spent on categories (if time tracking added)

### Priority 2: Recurring Todos (Beyond Dailies)
**Description:** Todos that repeat on custom schedules
- Weekly recurring todos (e.g., "Review budget every Sunday")
- Monthly recurring (e.g., "Pay rent on 1st")
- Custom intervals (every 2 weeks, quarterly)
- Different from dailies: has due date that advances

### Priority 3: Project/Workspace Module
**Description:** Group related items together
- Create projects that contain todos, goals, ideas, notes
- Project-level progress tracking
- Archive completed projects
- Project templates for common workflows
- Kanban board view for project tasks

### Priority 4: Time Tracking Integration
**Description:** Track time spent on todos and habits
- Start/stop timer on todos
- Manual time entry
- Daily/weekly time reports
- Integration with calendar for time blocking
- Pomodoro timer option

### Priority 6: Focus Mode / Do Not Disturb
**Description:** Distraction-free work sessions
- Hide all but selected items during focus
- Pomodoro-style focus sessions
- Block distracting features during focus
- Session history and statistics
- Integration with habits (focus session = habit increment)

### Priority 7: Calendar Week/Month View
**Description:** Native calendar visualization
- Week view showing todos, dailies, calendar events
- Month view with color-coded items
- Drag-and-drop to reschedule todos
- Quick add from calendar cells
- Export/print calendar views

### Priority 8: Templates System
**Description:** Reusable templates for common workflows
- Todo templates (with subtasks)
- Daily routine templates
- Goal templates with pre-defined milestones
- Project templates
- Import/export templates

### Priority 9: Tags & Categories System
**Description:** Cross-cutting organization
- Add tags to any entity (todos, ideas, goals, etc.)
- Color-coded tags
- Tag-based views and dashboards
- Smart tags (auto-assigned based on content)
- Tag statistics and usage

### Priority 10: Subtasks for Todos
**Description:** Break todos into smaller steps
- Checkbox subtasks within todos
- Progress based on completed subtasks
- Convert subtasks to standalone todos
- Indent/nest subtasks
- Subtask templates

### Priority 11: Collaboration Features
**Description:** Share and collaborate (multi-user enhancement)
- Share individual items with other users
- Assign todos to team members
- Shared shopping lists
- Comments on shared items
- Activity feed for shared items

### Priority 12: Import/Export System
**Description:** Data portability
- Export all data to JSON/CSV
- Import from other apps (Todoist, Habitica, Notion)
- Backup/restore functionality
- Markdown export for notes/ideas
- Google Takeout integration

### Priority 13: Gamification System
**Description:** Points, levels, achievements (Habitica-style)
- Experience points for completing tasks
- Levels with unlockable features/themes
- Achievement badges
- Daily/weekly challenges
- Leaderboard (for multi-user)

### Priority 14: API & Integrations
**Description:** Connect with external services
- Public REST API for automation
- Zapier/IFTTT integration
- Slack notifications
- GitHub integration (link commits to todos)
- Webhook support for custom integrations

### Priority 15: Natural Language Input
**Description:** Smart input parsing
- "Buy milk tomorrow" → creates todo due tomorrow
- "Exercise every Monday, Wednesday, Friday" → creates daily
- "Read 10 pages before bed" → creates habit
- Parse dates, priorities, tags from text
- Voice-to-task conversion

### Priority 16: Health & Wellness Module
**Description:** Track health-related metrics
- Water intake tracker
- Sleep logging
- Exercise minutes (tie to dailies)
- Weight/measurement tracking
- Mood check-ins
- Health dashboard with trends

### Priority 17: Finance Tracker Module
**Description:** Basic financial tracking
- Expense logging
- Budget categories
- Monthly spending overview
- Bill reminders (recurring todos)
- Savings goals (as Goal type)

### Priority 18: Reading List / Media Tracker
**Description:** Track books, movies, shows
- Reading list with progress
- Watchlist for movies/shows
- Currently reading/watching
- Reviews and ratings
- Recommendations integration

### Priority 19: Location-Based Reminders
**Description:** Contextual reminders
- "Remind me when I get to the store" → shopping list
- Home/work/gym location triggers
- Geofence-based notifications
- Location tags on todos
- "Errands nearby" smart list

### Priority 20: AI Assistant Integration
**Description:** Smart suggestions and automation
- AI task prioritization suggestions
- Auto-schedule based on patterns
- Smart daily planning assistant
- Natural language search
- Predictive task creation based on patterns
- Integration with Claude/ChatGPT for brainstorming in Ideas

---

## Implementation Notes

### Quick Wins (Low effort, high impact)
- Priority 2 (Todo Time Scheduling) - model already has some fields
- Priority 10 (Subtasks for Todos) - simple addition
- Priority 8 (Templates System) - builds on existing models

### High Impact, Higher Effort
- Priority 1 (Calendar Two-Way Sync) - requires OAuth enhancement
- Priority 1 (Weekly Review Dashboard) - needs new analytics queries
- Priority 3 (Project Module) - new model and relationships

### Foundation for Future Features
- Tags System (#9) enables many other features
- API (#14) enables integrations and mobile apps
- Templates (#8) enables faster user onboarding

---

## Suggested Phase 1 Implementation Order

1. **Todo Time Scheduling** - enhances daily use immediately
2. **Subtasks for Todos** - frequently requested feature
3. **Weekly Review Dashboard** - provides motivation/visibility
4. **Tags System** - foundation for organization
5. **Recurring Todos** - fills gap between todos and dailies
6. **Calendar Two-Way Sync** - completes the calendar story

This order balances quick wins with building blocks for future features.
