-- Database initialization script for Arbitrage Tool
-- This script sets up the database with necessary extensions and basic configuration

-- Create database if it doesn't exist (handled by docker-compose)
-- CREATE DATABASE arbitrage;

-- Connect to the arbitrage database
\c arbitrage;

-- Create necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create application user with limited privileges
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'arbitrage_app') THEN
        CREATE ROLE arbitrage_app WITH LOGIN PASSWORD 'app_secure_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE arbitrage TO arbitrage_app;
GRANT USAGE ON SCHEMA public TO arbitrage_app;
GRANT CREATE ON SCHEMA public TO arbitrage_app;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO arbitrage_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO arbitrage_app;

-- Create basic indexes that will be useful
-- (Note: Alembic migrations will create the actual tables and their indexes)

-- Set some performance-related settings
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Reload configuration
SELECT pg_reload_conf();

-- Create a basic health check function
CREATE OR REPLACE FUNCTION health_check()
RETURNS JSON AS $$
BEGIN
    RETURN json_build_object(
        'status', 'healthy',
        'timestamp', NOW(),
        'database', current_database(),
        'version', version()
    );
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission on health check function
GRANT EXECUTE ON FUNCTION health_check() TO arbitrage_app;

\echo 'Database initialization completed successfully!' 