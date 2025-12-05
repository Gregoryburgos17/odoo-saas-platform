-- ===========================================
-- PostgreSQL Initialization Script
-- Odoo SaaS Platform
-- ===========================================

-- Ensure the odoo user has the necessary permissions
ALTER USER odoo WITH CREATEDB;

-- Create extension for UUID generation (useful for Odoo)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a metadata database to track tenants (optional but useful)
CREATE DATABASE saas_metadata;

-- Connect to the metadata database and create the tenants table
\c saas_metadata;

CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    database_name VARCHAR(100) NOT NULL UNIQUE,
    subdomain VARCHAR(100) NOT NULL UNIQUE,
    admin_email VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_tenants_subdomain ON tenants(subdomain);
CREATE INDEX IF NOT EXISTS idx_tenants_database_name ON tenants(database_name);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE saas_metadata TO odoo;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO odoo;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO odoo;
