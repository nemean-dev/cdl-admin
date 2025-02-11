"""empty message

Revision ID: df341f2a1be6
Revises: deea039ff779
Create Date: 2025-02-11 09:58:02.089630

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df341f2a1be6'
down_revision = 'deea039ff779'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # ### end Alembic commands ###
    with op.batch_alter_table('vendor', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_products', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('total_variants', sa.Integer(), nullable=True))
    
    op.execute("UPDATE vendor SET total_products = 0")
    op.execute("UPDATE vendor SET total_variants = 0")

    with op.batch_alter_table('vendor',schema=None) as batch_op:
        batch_op.alter_column(sa.Column('total_products', sa.Integer(), nullable=False))
        batch_op.alter_column(sa.Column('total_variants', sa.Integer(), nullable=False))



def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('vendor', schema=None) as batch_op:
        batch_op.drop_column('total_variants')
        batch_op.drop_column('total_products')

    # ### end Alembic commands ###
