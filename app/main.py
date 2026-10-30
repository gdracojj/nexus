import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.services.licitacao_service import consultar_licitacoes


logger = logging.getLogger(__name__)
app = FastAPI(title="NEXUS")


@app.get("/api/licitacoes")
def listar_licitacoes(uf: str | None = None, produto: str = ""):

    uf = uf.strip().upper() if uf else None
    produto = produto.strip().lower()

    if uf is not None and len(uf) != 2:
        raise HTTPException(
            status_code=400,
            detail="Informe a sigla do estado com 2 letras.",
        )

    try:
        total_consultado, resultados, ultima_sincronizacao = consultar_licitacoes(
            estado=uf,
            produto=produto,
        )

    except Exception as erro:
        # A mensagem da exceção pode conter DSNs ou outros dados operacionais.
        logger.error("Falha na consulta persistida (tipo=%s).", type(erro).__name__)

        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a consulta.",
        ) from erro

    return {
        "uf": uf,
        "produto": produto,
        "total_consultado": total_consultado,
        "total": len(resultados),
        "resultados": resultados,
        "ultima_sincronizacao": ultima_sincronizacao,
    }


app.mount(
    "/",
    StaticFiles(
        directory=Path(__file__).resolve().parent.parent / "frontend",
        html=True,
    ),
    name="frontend",
)
