"""create gmaps_id field

Revision ID: cd8cc6c08265
Revises: 7efd213fddcb
Create Date: 2025-02-16 13:47:30.625028

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cd8cc6c08265"
down_revision = "7efd213fddcb"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.add_column(sa.Column("gmaps_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("open_hours", sa.String(), nullable=True))

    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.execute("DELETE FROM restaurant WHERE gmaps_id IS NULL")

    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.alter_column("gmaps_id", nullable=False)
        batch_op.create_unique_constraint(None, ["gmaps_id"])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="unique")
        batch_op.drop_column("open_hours")
        batch_op.drop_column("gmaps_id")

    # ### end Alembic commands ###
