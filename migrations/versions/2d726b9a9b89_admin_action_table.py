"""admin_action table

Revision ID: 2d726b9a9b89
Revises: 5d50d9ca795c
Create Date: 2025-01-13 22:34:42.178597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d726b9a9b89'
down_revision = '5d50d9ca795c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admin_action',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('action', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('admin_action', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_admin_action_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_admin_action_user_id'), ['user_id'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('admin_action', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_admin_action_user_id'))
        batch_op.drop_index(batch_op.f('ix_admin_action_timestamp'))

    op.drop_table('admin_action')
    # ### end Alembic commands ###
