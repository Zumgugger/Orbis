# Bugfixes & Features - January 26, 2026

## Issues to Fix

### 1. Settings Page - Active Modules & Google Account Overwriting Each Other
**Problem:** When saving Google account settings, active modules are reset (and vice versa) because each form only submits its own fields.

**Solution:** Combine all settings into a single form OR preserve existing values when one section is saved.

- [x] Modify settings page to use a single unified form
- [x] Ensure all fields (shared_calendar_id, default_google_account, active_modules) are submitted together
- [ ] Test saving each setting individually and together

---

### 2. Stats Dashboard with Fun Statistics
**Problem:** No historical tracking of progress, no motivation stats.

**Solution:** Create a new stats dashboard with fun statistics, filterable by tags.

- [x] Create new model `DailyStats` with fields: user_id, date, completed_count, total_count, percentage
- [x] Create database migration for DailyStats
- [x] Create stats blueprint and routes
- [x] Create stats.html template with fun statistics:
  - Total 100% days count
  - Current streak of productive days
  - Completion rate trends
  - Tag-based filtering
- [x] Add stats link to avatar dropdown menu in base.html
- [x] Add logic to save stats during rollover

---

### 3. Autosave for Ideas, Notes, Masterprompts, Shopping
**Problem:** User must manually click save button; content can be lost.

**Solution:** Implement autosave with debounced JavaScript (save 1-2 seconds after typing stops).

- [x] Add autosave JavaScript for Ideas notes editor (Quill)
- [ ] Add autosave for Notes content
- [ ] Add autosave for Masterprompts
- [ ] Add autosave for Shopping list items
- [x] No visual indicator needed per user request

---

### 4. Edit Ideas Should Show Description
**Problem:** The edit tab in idea view doesn't show the description field.

**Solution:** Add description field to the edit form in view.html (max 255 chars).

- [x] Add description textarea to ideas/view.html edit tab
- [x] Limit to 255 characters (to differentiate from notes)
- [x] Include in autosave functionality

---

### 5. Checklist Inside Ideas Notes
**Problem:** User wants a checklist feature inside ideas.

**Solution:** Add simple checklist feature within the notes section of ideas.

- [x] Add `checklist_data` JSON field to Idea model
- [x] Create database migration
- [x] Add checklist UI section in idea view (within notes tab)
- [x] Add/check/delete checklist items via AJAX
- [x] Keep separate from todo system - only visible inside the idea

---

### 6. Yesterday's Dailies - All Disappear When Clicking One
**Problem:** When checking one missed daily from yesterday, the entire alert/list disappears.

**Solution:** Use AJAX to complete individual dailies, show yesterday progress, fade out items.

- [x] Convert complete_yesterday to AJAX endpoint
- [x] Show individual item fading out after completion
- [x] Add yesterday's progress bar (shows how many were completed)
- [x] Keep dismiss button for remaining items

---

## Additional Tasks

- [x] **Update this todolist** as items are completed
- [ ] **Git commit and push** after all fixes are done

---

## Notes

- Offline functionality scheduled for next session
- Focus on database persistence over local storage where applicable
- Autosave for Notes, Masterprompts, Shopping still pending
