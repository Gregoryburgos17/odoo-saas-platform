-- PostgreSQL Initialization Script for Odoo SaaS Platform
-- This script runs automatically when the PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create additional databases for tenant isolation (if needed)
-- These would be created dynamically, but we set up the template

-- Set default timezone
SET timezone = 'UTC';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE odoo_saas TO odoo;

-- Create a function for automatic updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed at %', CURRENT_TIMESTAMP;
END $$;
