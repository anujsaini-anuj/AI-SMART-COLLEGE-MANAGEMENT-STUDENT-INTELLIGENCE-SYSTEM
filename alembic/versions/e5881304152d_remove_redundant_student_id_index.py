"""remove redundant student id index

Revision ID: e5881304152d
Revises: d2f5319a6e59
Create Date: 2026-09-21 13:31:57.227130

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'e5881304152d'
down_revision: Union[str, Sequence[str], None] = 'd2f5319a6e59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    pass

def downgrade() -> None:
    """Downgrade schema."""
    pass