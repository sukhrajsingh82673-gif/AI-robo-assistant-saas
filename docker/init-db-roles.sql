-- ============================================================================
-- ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
-- Database Role Provisioning & Least-Privilege Access Control
-- Enforces BLK-03: Separation of DDL, DML, and Backup Operations
-- ============================================================================

-- Ensure the primary production database exists
SELECT 'CREATE DATABASE zonata_production'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'zonata_production')\gexec

\connect zonata_production;

-- 1. Create Least-Privilege Application Role (zonata_app)
-- Restricted to DML operations (SELECT, INSERT, UPDATE, DELETE)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zonata_app') THEN
        CREATE ROLE zonata_app WITH LOGIN PASSWORD 'zonata_app_change_me_in_vault';
    END IF;
END $$;

-- 2. Create Least-Privilege Worker Role (zonata_worker)
-- Restricted to task queue, background jobs, and evidence ingestion
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zonata_worker') THEN
        CREATE ROLE zonata_worker WITH LOGIN PASSWORD 'zonata_worker_change_me_in_vault';
    END IF;
END $$;

-- 3. Create Dedicated Migration Role (zonata_migrator)
-- Holds DDL privileges for schema migrations only (never used at API runtime)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zonata_migrator') THEN
        CREATE ROLE zonata_migrator WITH LOGIN PASSWORD 'zonata_migrator_change_me_in_vault';
    END IF;
END $$;

-- 4. Create Dedicated Backup / Replication Role (zonata_backup)
-- Holds REPLICATION privileges and read-only access for pg_basebackup / WAL archiving
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'zonata_backup') THEN
        CREATE ROLE zonata_backup WITH REPLICATION LOGIN PASSWORD 'zonata_backup_change_me_in_vault';
    END IF;
END $$;

-- 5. Revoke default public schema create rights from non-admin roles
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM zonata_app;
REVOKE CREATE ON SCHEMA public FROM zonata_worker;
REVOKE CREATE ON SCHEMA public FROM zonata_backup;

-- 6. Grant DDL rights to Migration Role
GRANT CONNECT ON DATABASE zonata_production TO zonata_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO zonata_migrator;
ALTER DEFAULT PRIVILEGES FOR ROLE zonata_migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zonata_app;
ALTER DEFAULT PRIVILEGES FOR ROLE zonata_migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO zonata_app;
ALTER DEFAULT PRIVILEGES FOR ROLE zonata_migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zonata_worker;
ALTER DEFAULT PRIVILEGES FOR ROLE zonata_migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO zonata_worker;
ALTER DEFAULT PRIVILEGES FOR ROLE zonata_migrator IN SCHEMA public GRANT SELECT ON TABLES TO zonata_backup;

-- 7. Grant DML rights to Application Role
GRANT CONNECT ON DATABASE zonata_production TO zonata_app;
GRANT USAGE ON SCHEMA public TO zonata_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zonata_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO zonata_app;

-- 8. Grant DML rights to Worker Role
GRANT CONNECT ON DATABASE zonata_production TO zonata_worker;
GRANT USAGE ON SCHEMA public TO zonata_worker;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zonata_worker;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO zonata_worker;

-- 9. Grant Read-Only rights to Backup Role
GRANT CONNECT ON DATABASE zonata_production TO zonata_backup;
GRANT USAGE ON SCHEMA public TO zonata_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO zonata_backup;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO zonata_backup;
