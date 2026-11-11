-- Additive upgrade for existing databases. Fresh databases get these columns
-- from SQLAlchemy metadata. No data or result is rewritten.
ALTER TABLE runs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP NULL;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS claimed_by VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE runs ADD COLUMN IF NOT EXISTS claim_token VARCHAR(36) NOT NULL DEFAULT '';
