-- =============================================================================
-- Odoo SaaS Platform - Database Initialization Script
-- =============================================================================
-- This script runs when PostgreSQL container starts for the first time
-- It creates the necessary extensions and initial structure

-- Create required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Create schema for platform management (optional)
CREATE SCHEMA IF NOT EXISTS saas_platform;

-- Grant privileges to the default user
GRANT ALL PRIVILEGES ON SCHEMA saas_platform TO odoo;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA saas_platform TO odoo;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA saas_platform TO odoo;

-- Create audit log function for trigger-based auditing
CREATE OR REPLACE FUNCTION saas_platform.audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO saas_platform.audit_log (
            table_name, operation, new_data, changed_by, changed_at
        ) VALUES (
            TG_TABLE_NAME, 'INSERT', row_to_json(NEW), current_user, now()
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO saas_platform.audit_log (
            table_name, operation, old_data, new_data, changed_by, changed_at
        ) VALUES (
            TG_TABLE_NAME, 'UPDATE', row_to_json(OLD), row_to_json(NEW), current_user, now()
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO saas_platform.audit_log (
            table_name, operation, old_data, changed_by, changed_at
        ) VALUES (
            TG_TABLE_NAME, 'DELETE', row_to_json(OLD), current_user, now()
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit log table
CREATE TABLE IF NOT EXISTS saas_platform.audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for efficient audit queries
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON saas_platform.audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON saas_platform.audit_log(changed_at);

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
    RAISE NOTICE 'Extensions created: uuid-ossp, pg_trgm, unaccent';
    RAISE NOTICE 'Schema created: saas_platform';
END $$;
