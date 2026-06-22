-- 013_cisd_field.sql
-- Adds ict_cisd_present column to trades table.
-- Tracks whether a CISD (Change in State of Delivery) confirmation was present at entry.
-- Nullable, MNQ-only in practice — mirrors ict_smt_present / ict_tdo_aligned.

ALTER TABLE trades ADD COLUMN ict_cisd_present BOOLEAN;
