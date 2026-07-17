"""005_add_llm_usage_partitioned

Create llm_usage table partitioned by month on created_at (Task 3-5 FR-18).

per rules/performance.md: "high-volume tables partitioned by month from the
first migration, not retrofitted later."

Creates the parent table plus two child partitions: current month + next.
Future partitions are created by a scheduled cleanup/migration job.
"""

from datetime import date, timedelta, timezone
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "005_add_llm_usage_partitioned"
down_revision: str = "004_add_api_keys"
depends_on: Sequence[str] | None = None


def _month_name(d: date) -> str:
    return f"{d.year}_{d.month:02d}"


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _first_of_next_month(d: date) -> date:
    """Return the first day of the month after d's month."""
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def upgrade() -> None:
    now_utc = date.today()  # date part is sufficient for partition bounds
    current_m = _first_of_month(now_utc)
    next_m = _first_of_next_month(current_m)
    overnext_m = _first_of_next_month(next_m)

    cur = _month_name(current_m)
    nxt = _month_name(next_m)

    # ── parent table ────────────────────────────────────────────────────
    op.execute(
        f"""
        CREATE TABLE llm_usage (
            id              INTEGER GENERATED ALWAYS AS IDENTITY,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            provider        VARCHAR(80)  NOT NULL,
            model           VARCHAR(120) NOT NULL,
            api_key_id      UUID         REFERENCES api_keys(id) ON DELETE SET NULL,
            task            VARCHAR(80)  NOT NULL,
            tier            VARCHAR(20)  NOT NULL
                             CHECK (tier IN ('cheap', 'strong', 'embedding')),
            project_id      UUID,
            tokens_in       INTEGER      NOT NULL DEFAULT 0,
            tokens_out      INTEGER      NOT NULL DEFAULT 0,
            cost_estimate   NUMERIC(10,6) NOT NULL DEFAULT 0
                             CHECK (cost_estimate >= 0),
            latency_ms      INTEGER,
            success         BOOLEAN      NOT NULL DEFAULT true,
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )

    op.create_index("ix_llm_usage_provider", "llm_usage", ["provider"])
    op.create_index("ix_llm_usage_task", "llm_usage", ["task"])
    op.create_index(
        "ix_llm_usage_project",
        "llm_usage",
        ["project_id"],
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )
    op.create_index(
        "ix_llm_usage_created_at",
        "llm_usage",
        ["created_at"],
        postgresql_using="brin",
    )

    # ── initial child partitions (current month + next month) ─────────────
    for child, frm, to in [
        (cur, current_m, next_m),
        (nxt, next_m, overnext_m),
    ]:
        op.execute(
            f"""
            CREATE TABLE llm_usage_{child}
                PARTITION OF llm_usage
                FOR VALUES FROM ('{frm} 00:00:00+00')
                             TO   ('{to} 00:00:00+00')
            """
        )


def downgrade() -> None:
    # Drop all child partitions then the parent (dynamic lookup by pg_inherits)
    op.execute(
        """
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT inhrelid::regclass::text AS child
                FROM pg_inherits
                WHERE inhparent = 'llm_usage'::regclass
            LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || r.child;
            END LOOP;
        END$$;
        """
    )
    op.drop_table("llm_usage")
