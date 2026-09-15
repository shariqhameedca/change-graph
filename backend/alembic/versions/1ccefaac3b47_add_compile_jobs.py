"""add compile jobs

Revision ID: 1ccefaac3b47
Revises: 6b3716c3872d
Create Date: 2026-09-14 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1ccefaac3b47'
down_revision = '6b3716c3872d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('compile_jobs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('regulation_id', sa.UUID(), nullable=False),
    sa.Column('regulation_version_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('current_step', sa.String(length=255), nullable=True),
    sa.Column('chunks_total', sa.Integer(), nullable=False),
    sa.Column('chunks_completed', sa.Integer(), nullable=False),
    sa.Column('chunks_failed', sa.Integer(), nullable=False),
    sa.Column('llm_provider', sa.String(length=50), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('total_input_tokens', sa.Integer(), nullable=True),
    sa.Column('total_output_tokens', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['regulation_id'], ['regulations.id'], ),
    sa.ForeignKeyConstraint(['regulation_version_id'], ['regulation_versions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_compile_jobs_regulation_version_id'), 'compile_jobs', ['regulation_version_id'], unique=False)
    op.create_table('compile_job_chunks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('compile_job_id', sa.UUID(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('char_start', sa.Integer(), nullable=False),
    sa.Column('char_end', sa.Integer(), nullable=False),
    sa.Column('raw_response', sa.Text(), nullable=True),
    sa.Column('rules_extracted', sa.Integer(), nullable=False),
    sa.Column('definitions_extracted', sa.Integer(), nullable=False),
    sa.Column('exceptions_extracted', sa.Integer(), nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('input_tokens', sa.Integer(), nullable=True),
    sa.Column('output_tokens', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['compile_job_id'], ['compile_jobs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('compile_job_id', 'chunk_index')
    )


def downgrade() -> None:
    op.drop_table('compile_job_chunks')
    op.drop_index(op.f('ix_compile_jobs_regulation_version_id'), table_name='compile_jobs')
    op.drop_table('compile_jobs')
