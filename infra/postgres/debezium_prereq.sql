-- CDC (Debezium): replication connection + logical decoding.
-- Runs after init.sql (alphabetical: z- prefix). Idempotent for superuser.
ALTER ROLE melisim WITH REPLICATION;
