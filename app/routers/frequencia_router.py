from fastapi import APIRouter, HTTPException, Request

from app.services.loader import carregar_parquet
from app.services import frequencia


router = APIRouter()

df = carregar_parquet()

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
    
@router.get("/absoluta")
def endpoint_frequencia_absoluta(
    request: Request
):

    colunas, filtros = preparar_parametros(request)

    try:
        resultado = frequencia.frequencia_absoluta(
            df,
            colunas,
            filtros
        )

        return {
            "colunas": colunas,
            "filtros": filtros,
            "resultado": resultado
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )


@router.get("/relativa")
def frequencia_relativa_endpoint(
    request: Request
):

    colunas, filtros = preparar_parametros(request)

    try:
        resultado = frequencia.frequencia_relativa(
            df,
            colunas,
            filtros
        )

        return {
            "colunas": colunas,
            "filtros": filtros,
            "resultado": resultado
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )


@router.get("/absoluta-acumulada")
def frequencia_absoluta_acumulada_endpoint(
    request: Request
):

    colunas, filtros = preparar_parametros(request)

    try:
        resultado = frequencia.frequencia_absoluta_acumulada(
            df,
            colunas,
            filtros
        )

        return {
            "colunas": colunas,
            "filtros": filtros,
            "resultado": resultado
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )


@router.get("/relativa-acumulada")
def frequencia_relativa_acumulada_endpoint(
    request: Request
):

    colunas, filtros = preparar_parametros(request)

    try:
        resultado = frequencia.frequencia_relativa_acumulada(
            df,
            colunas,
            filtros
        )

        return {
            "colunas": colunas,
            "filtros": filtros,
            "resultado": resultado
        }

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )