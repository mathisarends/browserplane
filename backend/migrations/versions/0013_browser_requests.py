"""Persist browser demand and wake consumers after committed capacity changes."""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "browser_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("test_run_id", sa.Uuid()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_id", sa.Uuid()),
        sa.Column("browser_id", sa.Uuid()),
        sa.Column("authentication_profile_id", sa.Uuid()),
        sa.Column("browser_checkpoint_id", sa.Uuid()),
        sa.Column("retry_at", sa.DateTime(timezone=True)),
        sa.Column("resume_session_id", sa.Uuid()),
        sa.CheckConstraint("status IN ('QUEUED','PROVISIONING','ASSIGNED','CANCELLED','EXPIRED')"),
        sa.CheckConstraint("(status = 'ASSIGNED') = (lease_id IS NOT NULL)"),
    )
    op.create_index("ix_browser_requests_owner_id", "browser_requests", ["owner_id"])
    op.create_index("ix_browser_requests_fifo", "browser_requests", ["created_at", "id"],
                    postgresql_where=sa.text("status = 'QUEUED'"))
    op.create_index("uq_browser_requests_provisioning", "browser_requests", ["browser_id"],
                    unique=True, postgresql_where=sa.text("browser_id IS NOT NULL"))
    op.execute("""
        CREATE FUNCTION notify_browser_capacity() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_notify('browser_capacity_changed', '');
            RETURN NULL;
        END $$
    """)
    for table in ("browser_requests", "browsers", "leases"):
        op.execute(f"CREATE TRIGGER {table}_notify AFTER INSERT OR UPDATE OR DELETE "
                   f"ON {table} FOR EACH ROW EXECUTE FUNCTION notify_browser_capacity()")


def downgrade():
    for table in ("browser_requests", "browsers", "leases"):
        op.execute(f"DROP TRIGGER {table}_notify ON {table}")
    op.execute("DROP FUNCTION notify_browser_capacity()")
    op.drop_table("browser_requests")
