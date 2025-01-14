"""empty message

Revision ID: f91d7e52e949
Revises: 2d726b9a9b89
Create Date: 2025-01-14 20:45:51.325421

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f91d7e52e949'
down_revision = '2d726b9a9b89'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default='0'))
        # added server_default to prevent error:
            #sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) Cannot add a NOT NULL column with default value NULL
            #[SQL: ALTER TABLE user ADD COLUMN is_superadmin BOOLEAN NOT NULL]
        # then remove server default
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('is_superadmin', server_default=None)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_superadmin')

    # ### end Alembic commands ###
