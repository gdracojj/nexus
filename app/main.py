import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from app.services.licitacao_service import consultar_licitacoes


logger = logging.getLogger(__name__)
app = FastAPI(title="NEXUS")


@app.get("/api/licitacoes")
def listar_licitacoes(
    uf: str | None = None,
    produto: str = "",
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=25, ge=1, le=100),
    prazo_dias: int | None = Query(default=None, ge=1, le=30),
):
    uf = uf.strip().upper() if uf else None
    produto = produto.strip().lower()

    if uf is not None and len(uf) != 2:
        raise HTTPException(
            status_code=400,
            detail="Informe a sigla do estado com 2 letras.",
        )

    try:
        (
            total_consultado,
            total,
            resultados,
            ultima_sincronizacao,
        ) = consultar_licitacoes(
            estado=uf,
            produto=produto,
            page=page,
            page_size=page_size,
            prazo_dias=prazo_dias,
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
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
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
