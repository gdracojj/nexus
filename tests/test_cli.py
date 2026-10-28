import pytest

from app.cli import main
from app.repositories import licitacao_repository
from app.services import licitacao_service


def test_coleta_nao_inicia_quando_o_lock_global_esta_ocupado(monkeypatch):
    def lock_ocupado():
        raise licitacao_repository.ColetaPNCPJaEmAndamentoError(
            "Já existe uma coleta PNCP em andamento."
        )

    def execucao_nao_esperada(*_args, **_kwargs):
        pytest.fail("não deve criar histórico para uma coleta que não iniciou")

    monkeypatch.setattr(licitacao_repository, "lock_coleta_pncp", lock_ocupado)
    monkeypatch.setattr(licitacao_repository, "iniciar_execucao", execucao_nao_esperada)

    with pytest.raises(licitacao_repository.ColetaPNCPJaEmAndamentoError):
        licitacao_service.sincronizar_licitacoes("RJ")


def test_cli_coleta_retorna_codigo_zero_em_sucesso(monkeypatch, capsys):
    chamadas = []
    monkeypatch.setattr(
        "app.cli.sincronizar_licitacoes",
        lambda uf: chamadas.append(uf) or 12,
    )

    codigo = main(["coletar", "--uf", " rj "])

    assert codigo == 0
    assert chamadas == ["RJ"]
    assert "12 registros processados" in capsys.readouterr().out


def test_cli_coleta_falha_sem_expor_detalhes_da_excecao(monkeypatch, capsys):
    def falhar(_uf):
        raise RuntimeError("postgresql://usuario:senha-secreta@host/db")

    monkeypatch.setattr("app.cli.sincronizar_licitacoes", falhar)

    codigo = main(["coletar", "--uf", "SP"])
    saida = capsys.readouterr()

    assert codigo == 1
    assert "RuntimeError" in saida.err
    assert "senha-secreta" not in saida.err
