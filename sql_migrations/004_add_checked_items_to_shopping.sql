-- Add checked_items column to shopping_lists table for persistent checkmark state
ALTER TABLE shopping_lists ADD COLUMN checked_items TEXT DEFAULT '';
