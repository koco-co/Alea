-- Enum values must be committed before a later migration can use them in
-- constraints or data changes.
alter type provider_execution_mode add value if not exists 'cli';
