"""Initial schema creation

Revision ID: 001
Revises: 
Create Date: 2025-12-14 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""
    
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Observations table
    op.create_table(
        'observations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.String(255), nullable=False),
        sa.Column('sender', sa.String(255), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_id', name='uq_email_id'),
    )
    op.create_index('idx_observations_email_id', 'observations', ['email_id'])
    op.create_index('idx_observations_sender', 'observations', ['sender'])
    op.create_index('idx_observations_created_at', 'observations', ['created_at'])
    
    # Email actions table
    op.create_table(
        'email_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('observation_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['observation_id'], ['observations.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_email_actions_observation_id', 'email_actions', ['observation_id'])
    op.create_index('idx_email_actions_status', 'email_actions', ['status'])
    op.create_index('idx_email_actions_action_type', 'email_actions', ['action_type'])
    
    # Embeddings table (pgvector)
    op.create_table(
        'embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('observation_id', sa.Integer(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['observation_id'], ['observations.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_embeddings_observation_id', 'embeddings', ['observation_id'])
    
    # Analysis results table
    op.create_table(
        'analysis_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('observation_id', sa.Integer(), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('result_json', postgresql.JSONB(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['observation_id'], ['observations.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_analysis_results_observation_id', 'analysis_results', ['observation_id'])
    op.create_index('idx_analysis_results_model', 'analysis_results', ['model'])
    op.create_index('idx_analysis_results_created_at', 'analysis_results', ['created_at'])


def downgrade() -> None:
    """Rollback initial schema."""
    op.drop_table('analysis_results')
    op.drop_table('embeddings')
    op.drop_table('email_actions')
    op.drop_table('observations')
    op.execute('DROP EXTENSION IF EXISTS vector')
