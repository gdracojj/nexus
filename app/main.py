from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.services.licitacao_service import buscar_e_filtrar_licitacoes


app = FastAPI(title="NEXUS")


@app.get("/api/licitacoes")
def listar_licitacoes(uf: str, produto: str = ""):

    uf = uf.strip().upper()
    produto = produto.strip().lower()

    if len(uf) != 2:
        raise HTTPException(
            status_code=400,
            detail="Informe a sigla do estado com 2 letras.",
        )

    try:
        dados, resultados = buscar_e_filtrar_licitacoes(
            estado=uf,
            produto=produto,
        )

    except Exception as erro:
        print(f"ERRO PNCP: {erro}")

        raise HTTPException(
            status_code=502,
            detail=str(erro),
        )

    return {
        "uf": uf,
        "produto": produto,
        "total_consultado": len(dados),
        "total": len(resultados),
        "resultados": resultados,
    }


app.mount(
    "/",
    StaticFiles(
        directory="frontend",
        html=True,
    ),
    name="frontend",
)