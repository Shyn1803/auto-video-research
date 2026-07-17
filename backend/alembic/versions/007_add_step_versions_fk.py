"""007_add_step_versions_fk

Fix pre-existing gap: 001_create_projects created step_versions.project_id
without a ForeignKeyConstraint to projects.id (the ORM model's relationship()
already assumed one existed, which broke SQLAlchemy mapper configuration the
first time anything triggered a full mapper configure pass — see Task 5-1
retrospective).
"""

from typing import Sequence

from alembic import op

revision: str = "007_add_step_versions_fk"
down_revision: str = "006_add_scene_approvals"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_step_versions_project",
        "step_versions",
        "projects",
        ["project_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_step_versions_project", "step_versions", type_="foreignkey")
