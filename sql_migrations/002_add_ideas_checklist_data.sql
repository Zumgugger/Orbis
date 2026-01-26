-- Migration 002: Add checklist_data column to ideas
-- This column was added for the checklist feature but never migrated to production

ALTER TABLE ideas ADD COLUMN checklist_data TEXT;
