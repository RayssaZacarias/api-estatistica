from fastapi import APIRouter, HTTPException, Request

from app.services.loader import carregar_parquet
from app.services import posicao
from app.utils import parametros

router = APIRouter()

df = carregar_parquet()

@router.get("/maximo")
def endpoint_maximo(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = posicao.maximo(df, colunas, filtros)

        return{
            "colunas": colunas,
            "filtros": filtros,
            "resultado": resultado
        }
    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )

@router.get("/minimo")
def endpoint_minimo(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = posicao.minimo(df, colunas, filtros)

        return{
            "colunas": colunas,
            "filtros": filtros,
            "resultado": resultado
        }
    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )

@router.get("/quartis")
def endpoint_quartis(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = posicao.quartis(df, colunas, filtros)

        return{
            "colunas": colunas,
            "filtros": filtros,
            "resultado": resultado
        }
    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )
