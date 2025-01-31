"""empty message

Revision ID: 331a10a734b9
Revises: 
Create Date: 2025-01-31 21:32:03.936400

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '331a10a734b9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('User', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=64), nullable=False))
        batch_op.drop_index('ix_User_Username')
        batch_op.create_index(batch_op.f('ix_User_username'), ['username'], unique=True)
        batch_op.drop_column('Username')

    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))
        batch_op.drop_index('ix_post_User_id')
        batch_op.create_index(batch_op.f('ix_post_user_id'), ['user_id'], unique=False)
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'User', ['user_id'], ['id'])
        batch_op.drop_column('User_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('User_id', sa.INTEGER(), nullable=False))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'User', ['User_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_post_user_id'))
        batch_op.create_index('ix_post_User_id', ['User_id'], unique=False)
        batch_op.drop_column('user_id')

    with op.batch_alter_table('User', schema=None) as batch_op:
        batch_op.add_column(sa.Column('Username', sa.VARCHAR(length=64), nullable=False))
        batch_op.drop_index(batch_op.f('ix_User_username'))
        batch_op.create_index('ix_User_Username', ['Username'], unique=1)
        batch_op.drop_column('username')

    # ### end Alembic commands ###
