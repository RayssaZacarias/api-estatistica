from fastapi import HTTPException, Request

def preparar_parametros(request: Request):

    parametros = dict(request.query_params)

    if "coluna" not in parametros:
        raise HTTPException(
            status_code=400,
            detail="Informe pelo menos uma coluna para analisar."
        )

    texto_colunas = parametros.pop("coluna")

    colunas = [
        coluna.strip()
        for coluna in texto_colunas.split(",")
        if coluna.strip()
    ]

    if not colunas:
        raise HTTPException(
            status_code=400,
            detail="Informe pelo menos uma coluna válida."
        )

    filtros = parametros

    return colunas, filtros