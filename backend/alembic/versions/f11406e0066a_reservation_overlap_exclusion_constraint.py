"""reservation overlap exclusion constraint

Stops two bookings holding the same unit on the same night at the database
level. The service layer already rejects clashes, but it does so by reading
before writing — two concurrent requests can both find the unit free.

The status predicate is frozen here on purpose: it mirrors
BLOCKING_RESERVATION_STATUSES at the time of writing. Adding a status that
should block a unit needs a new migration to rebuild the constraint.

Revision ID: f11406e0066a
Revises: c364d271c054
Create Date: 2026-08-12 20:35:47.424738
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'f11406e0066a'
down_revision: Union[str, None] = 'c364d271c054'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ex_reservations_no_overlap"


def upgrade() -> None:
    # Needed to mix the `unit_id =` equality into a GiST index alongside the
    # range overlap operator.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        f"""
        ALTER TABLE reservations
        ADD CONSTRAINT {CONSTRAINT_NAME}
        EXCLUDE USING gist (
            unit_id WITH =,
            daterange(check_in_date, check_out_date, '[)') WITH &&
        )
        WHERE (status IN ('checked_out', 'confirmed', 'in_house', 'pending'))
        """
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE reservations DROP CONSTRAINT {CONSTRAINT_NAME}")
    # btree_gist is left installed: other objects may depend on it, and
    # dropping an extension is not this migration's business to undo.
