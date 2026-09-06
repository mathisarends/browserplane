"""Name browser demand what it produces: a session request."""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

# Renaming a column rewrites the check constraints that read it, but leaves
# every constraint and index carrying the table's old name. Rename them by
# pattern: their generated names are Postgres's business, not this file's.
RENAME_OBJECTS = """
DO $$
DECLARE name text;
BEGIN
    FOR name IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = '{new}'::regclass AND starts_with(conname, '{old}')
    LOOP
        EXECUTE 'ALTER TABLE {new} RENAME CONSTRAINT ' || quote_ident(name)
             || ' TO ' || quote_ident(replace(name, '{old}', '{new}'));
    END LOOP;
    FOR name IN
        SELECT indexname FROM pg_indexes
        WHERE tablename = '{new}' AND strpos(indexname, '{old}') > 0
    LOOP
        EXECUTE 'ALTER INDEX ' || quote_ident(name)
             || ' RENAME TO ' || quote_ident(replace(name, '{old}', '{new}'));
    END LOOP;
END $$
"""
# The trigger function stays shared with browsers and leases under its own name.
NOTIFY_TRIGGER = (
    "CREATE TRIGGER {table}_notify AFTER INSERT OR UPDATE OR DELETE "
    "ON {table} FOR EACH ROW EXECUTE FUNCTION notify_browser_capacity()"
)


def upgrade():
    op.execute("DROP TRIGGER browser_requests_notify ON browser_requests")
    op.rename_table("browser_requests", "session_requests")
    op.alter_column("session_requests", "lease_id", new_column_name="session_id")
    op.execute(RENAME_OBJECTS.format(old="browser_requests", new="session_requests"))
    op.execute(NOTIFY_TRIGGER.format(table="session_requests"))


def downgrade():
    op.execute("DROP TRIGGER session_requests_notify ON session_requests")
    op.alter_column("session_requests", "session_id", new_column_name="lease_id")
    op.rename_table("session_requests", "browser_requests")
    op.execute(RENAME_OBJECTS.format(old="session_requests", new="browser_requests"))
    op.execute(NOTIFY_TRIGGER.format(table="browser_requests"))
