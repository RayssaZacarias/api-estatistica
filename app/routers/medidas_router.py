from fastapi import APIRouter, HTTPException, Request

from app.services.loader import carregar_parquet
from app.services import medidas
from app.utils import parametros

router = APIRouter()

df = carregar_parquet()

@router.get("/media")
def endpoint_media(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = medidas.media(df,colunas, filtros)


        return{
            "colunas": colunas,
            "filtros":filtros,
            "resultado":resultado
        }
    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )

@router.get("/moda")
def endpoint_moda(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = medidas.moda(df, colunas, filtros)

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


@router.get("/mediana")
def endpoint_mediana(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = medidas.mediana(df, colunas, filtros)

        return{
            "colunas": colunas,
            "filtros": filtros,
            "resultado":resultado
        }
    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )