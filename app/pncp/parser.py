def normalizar_licitacao(licitacao):
    return {
        "numero": licitacao["numeroCompra"],
        "descricao": licitacao["objetoCompra"],
        "codigo_unidade": licitacao["unidadeOrgao"]["codigoUnidade"],
        "municipio": licitacao["unidadeOrgao"]["municipioNome"],
        "uf": licitacao["unidadeOrgao"]["ufSigla"],
        "data_encerramento_proposta": licitacao["dataEncerramentoProposta"],
    }