from fastapi import APIRouter, HTTPException, Request

from app.services.loader import carregar_parquet
from app.services import frequencia
from app.utils import parametros


router = APIRouter()

df = carregar_parquet()
    
@router.get("/absoluta")
def endpoint_frequencia_absoluta(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = frequencia.frequencia_absoluta(df,colunas,filtros
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
def frequencia_relativa_endpoint(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = frequencia.frequencia_relativa(df,colunas,filtros)

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
def frequencia_absoluta_acumulada_endpoint(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = frequencia.frequencia_absoluta_acumulada(df,colunas,filtros)

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
def frequencia_relativa_acumulada_endpoint(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

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