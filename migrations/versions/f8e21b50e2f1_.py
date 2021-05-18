"""empty message

Revision ID: f8e21b50e2f1
Revises: c388939858d5
Create Date: 2021-05-15 14:29:38.836951

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8e21b50e2f1'
down_revision = 'c388939858d5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('exam_form',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('form_description', sa.String(), nullable=False),
    sa.Column('parent_user_id', sa.Integer(), nullable=False),
    sa.Column('proctor_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['parent_user_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['proctor_id'], ['proctor_session.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('form_description')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('exam_form')
    # ### end Alembic commands ###
