CREATE INDEX idx_users_email_lower ON users (LOWER(email));

CREATE INDEX idx_users_active_created ON users (created_at DESC) WHERE status = 'active';