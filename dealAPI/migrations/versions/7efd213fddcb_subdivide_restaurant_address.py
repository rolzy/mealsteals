"""subdivide restaurant address

Revision ID: 7efd213fddcb
Revises: eea0316ac44b
Create Date: 2025-01-14 06:46:41.985836

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7efd213fddcb"
down_revision = "eea0316ac44b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.add_column(sa.Column("street_address", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("suburb", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("state", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("postcode", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("country", sa.String(), nullable=True))
        batch_op.drop_column("address")

    # Set default values for existing records
    op.execute(
        "UPDATE restaurant SET street_address = 'Unknown' WHERE street_address IS NULL"
    )
    op.execute("UPDATE restaurant SET suburb = 'Unknown' WHERE suburb IS NULL")
    op.execute("UPDATE restaurant SET state = 'Unknown' WHERE state IS NULL")
    op.execute("UPDATE restaurant SET postcode = 'Unknown' WHERE postcode IS NULL")
    op.execute("UPDATE restaurant SET country = 'Unknown' WHERE country IS NULL")

    # Make columns non-nullable after setting default values
    op.alter_column("restaurant", "street_address", nullable=False)
    op.alter_column("restaurant", "suburb", nullable=False)
    op.alter_column("restaurant", "state", nullable=False)
    op.alter_column("restaurant", "postcode", nullable=False)
    op.alter_column("restaurant", "country", nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("address", sa.VARCHAR(), autoincrement=False, nullable=False)
        )
        batch_op.drop_column("country")
        batch_op.drop_column("postcode")
        batch_op.drop_column("state")
        batch_op.drop_column("suburb")
        batch_op.drop_column("street_address")

    # ### end Alembic commands ###
