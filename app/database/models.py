from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Licitacao(Base):
    __tablename__ = "licitacoes"
    __table_args__ = (
        UniqueConstraint("numero_controle_pncp", name="uq_licitacoes_numero_controle_pncp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_controle_pncp: Mapped[str] = mapped_column(String(40), nullable=False)
    cnpj_orgao: Mapped[str | None] = mapped_column(String(14))
    nome_orgao: Mapped[str | None] = mapped_column(String(500))
    codigo_modalidade: Mapped[int | None] = mapped_column(Integer)
    numero: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo_unidade: Mapped[str | None] = mapped_column(String(100))
    ano: Mapped[int | None] = mapped_column(Integer)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    municipio: Mapped[str | None] = mapped_column(String(200))
    data_publicacao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_abertura_proposta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_encerramento_proposta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valor_estimado: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    situacao: Mapped[str | None] = mapped_column(String(200))
    ultima_execucao_id: Mapped[int | None] = mapped_column(ForeignKey("sync_execucoes.id", ondelete="SET NULL"))
    coletada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    payload: Mapped["PncpPayload"] = relationship(back_populates="licitacao", cascade="all, delete-orphan", uselist=False)


class PncpPayload(Base):
    __tablename__ = "pncp_payloads"

    licitacao_id: Mapped[int] = mapped_column(ForeignKey("licitacoes.id", ondelete="CASCADE"), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    licitacao: Mapped[Licitacao] = relationship(back_populates="payload")


class SyncExecucao(Base):
    __tablename__ = "sync_execucoes"
    __table_args__ = (
        CheckConstraint("status IN ('executando', 'concluida', 'parcial', 'falhou')", name="ck_sync_execucoes_status"),
        CheckConstraint(
            "paginas_consultadas >= 0 AND registros_recebidos >= 0 "
            "AND registros_processados >= 0 AND registros_com_erro >= 0",
            name="ck_sync_execucoes_contagens_nao_negativas",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(300), nullable=False)
    parametros: Mapped[dict] = mapped_column(JSONB, nullable=False)
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="executando")
    paginas_consultadas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registros_recebidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registros_processados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registros_com_erro: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resumo_falhas: Mapped[dict | None] = mapped_column(JSONB)
