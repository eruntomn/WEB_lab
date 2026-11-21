CREATE UNIQUE INDEX idx_users_email ON users (email);

CREATE INDEX idx_registrations_course_id ON registrations (course_id, id DESC);