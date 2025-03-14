"""Make deals components optional

Revision ID: c267e527659f
Revises: ed0e170b8ec7
Create Date: 2025-03-04 06:10:49.627824

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c267e527659f'
down_revision = 'ed0e170b8ec7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('deal', schema=None) as batch_op:
        batch_op.drop_column('last_updated')

    with op.batch_alter_table('restaurant', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deals_last_updated', sa.DateTime(timezone=True), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('restaurant', schema=None) as batch_op:
        batch_op.drop_column('deals_last_updated')

    with op.batch_alter_table('deal', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_updated', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False))

    # ### end Alembic commands ###
