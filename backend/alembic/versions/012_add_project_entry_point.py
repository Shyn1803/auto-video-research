"""012_add_project_entry_point

Add `entry_point` column to projects table (Task 4-8, BR-4).
Values: 'research' (default, existing flow) or 'script' (paste script entry).
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "012_add_project_entry_point"
down_revision: str = "011_add_claims"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "entry_point",
            sa.String(20),
            nullable=False,
            server_default="research",
        ),
    )
    op.create_check_constraint(
        "ck_projects_entry_point",
        "projects",
        "entry_point IN ('research', 'script')",
    )
    op.create_index("idx_projects_entry_point", "projects", ["entry_point"])


def downgrade() -> None:
    op.drop_index("idx_projects_entry_point", table_name="projects")
    op.drop_constraint("ck_projects_entry_point", "projects", type_="CHECK")
    op.drop_column("projects", "entry_point")
