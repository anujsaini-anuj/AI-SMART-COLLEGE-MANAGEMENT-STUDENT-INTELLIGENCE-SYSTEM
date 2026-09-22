"""initial database baseline

Revision ID: d2f5319a6e59
Revises:
Create Date: 2026-09-21 13:12:13.857116
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d2f5319a6e59"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Synchronize existing database schema with current SQLAlchemy models.
    """

    # ---------------------------------------------------------
    # 1. predictions.prediction_type
    # ---------------------------------------------------------

    op.alter_column(
        "predictions",
        "prediction_type",
        existing_type=sa.VARCHAR(length=100),
        nullable=False,
        existing_server_default=sa.text(
            "'Current Performance'::character varying"
        ),
    )

    # ---------------------------------------------------------
    # 2. students.course_id
    # VARCHAR -> INTEGER
    # ---------------------------------------------------------

    op.alter_column(
        "students",
        "course_id",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="course_id::integer",
    )

    # ---------------------------------------------------------
    # 3. students.course_id -> courses.id
    # Foreign Key
    # ---------------------------------------------------------

    op.create_foreign_key(
        "students_course_id_fkey",
        "students",
        "courses",
        ["course_id"],
        ["id"],
    )

    # ---------------------------------------------------------
    # 4. users.created_at
    # TIMESTAMP -> TIMESTAMP WITH TIME ZONE
    # ---------------------------------------------------------

    op.alter_column(
        "users",
        "created_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        nullable=False,
    )


def downgrade() -> None:
    """
    Reverse the schema changes.
    """

    # ---------------------------------------------------------
    # 1. Remove students.course_id foreign key
    # ---------------------------------------------------------

    op.drop_constraint(
        "students_course_id_fkey",
        "students",
        type_="foreignkey",
    )

    # ---------------------------------------------------------
    # 2. INTEGER -> VARCHAR
    # ---------------------------------------------------------

    op.alter_column(
        "students",
        "course_id",
        existing_type=sa.Integer(),
        type_=sa.VARCHAR(length=100),
        existing_nullable=False,
        postgresql_using="course_id::varchar",
    )

    # ---------------------------------------------------------
    # 3. users.created_at
    # TIMEZONE -> NON-TIMEZONE
    # ---------------------------------------------------------

    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        nullable=True,
    )

    # ---------------------------------------------------------
    # 4. predictions.prediction_type
    # ---------------------------------------------------------

    op.alter_column(
        "predictions",
        "prediction_type",
        existing_type=sa.VARCHAR(length=100),
        nullable=True,
        existing_server_default=sa.text(
            "'Current Performance'::character varying"
        ),
    )