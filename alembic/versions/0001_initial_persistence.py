"""Initial PNCP persistence schema.

Revision ID: 0001_initial_persistence
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_persistence"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_execucoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("endpoint", sa.String(length=300), nullable=False),
        sa.Column("parametros", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finalizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("paginas_consultadas", sa.Integer(), nullable=False),
        sa.Column("registros_recebidos", sa.Integer(), nullable=False),
        sa.Column("registros_processados", sa.Integer(), nullable=False),
        sa.Column("registros_com_erro", sa.Integer(), nullable=False),
        sa.Column("resumo_falhas", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("status IN ('executando', 'concluida', 'parcial', 'falhou')", name="ck_sync_execucoes_status"),
        sa.CheckConstraint("paginas_consultadas >= 0 AND registros_recebidos >= 0 AND registros_processados >= 0 AND registros_com_erro >= 0", name="ck_sync_execucoes_contagens_nao_negativas"),
    )
    op.create_table(
        "licitacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero_controle_pncp", sa.String(length=40), nullable=False),
        sa.Column("cnpj_orgao", sa.String(length=14), nullable=True),
        sa.Column("nome_orgao", sa.String(length=500), nullable=True),
        sa.Column("codigo_modalidade", sa.Integer(), nullable=True),
        sa.Column("numero", sa.String(length=100), nullable=False),
        sa.Column("codigo_unidade", sa.String(length=100), nullable=True),
        sa.Column("ano", sa.Integer(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("municipio", sa.String(length=200), nullable=True),
        sa.Column("data_publicacao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_abertura_proposta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_encerramento_proposta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valor_estimado", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("situacao", sa.String(length=200), nullable=True),
        sa.Column("ultima_execucao_id", sa.Integer(), nullable=True),
        sa.Column("coletada_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ultima_execucao_id"], ["sync_execucoes.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("numero_controle_pncp", name="uq_licitacoes_numero_controle_pncp"),
    )
    op.create_table(
        "pncp_payloads",
        sa.Column("licitacao_id", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("recebido_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["licitacao_id"], ["licitacoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("licitacao_id"),
    )


def downgrade() -> None:
    op.drop_table("pncp_payloads")
    op.drop_table("licitacoes")
    op.drop_table("sync_execucoes")
