"""012_add_pipeline_run_cancel_requested_at

Add pipeline_runs.cancel_requested_at -- Task 4-7 Step 2. A cancel request
is recorded as a timestamp rather than a transient "cancelling" status value
(no CHECK-constraint churn on ck_pipeline_runs_status, and it survives a
crash between "cancel requested" and "node actually stopped" without any
ambiguity about which happened first). RunService checks this column right
after the current node's ``graph.ainvoke()`` call returns, before writing
the node's completion transition (BR-1: finish after the in-flight node,
never mid-write).

Epic 4, task 4-7.
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "012_add_pipeline_run_cancel_requested_at"
down_revision: str = "011_add_claims"
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_runs",
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_runs", "cancel_requested_at")
