"""Auth accounts only; profile data belongs to future user management."""
from alembic import op
import sqlalchemy as sa
revision = '0001_user_account'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('user_account',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('phone', sa.String(11), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.UniqueConstraint('phone', name='uq_user_account_phone'),
        sa.CheckConstraint("role IN ('STUDENT', 'PARENT', 'STAFF')", name='ck_account_role'))

def downgrade():
    op.drop_table('user_account')
