from fastapi import APIRouter, HTTPException, Request

from app.services.loader import carregar_parquet
from app.services import dispersao
from app.utils import parametros

router = APIRouter()

df = carregar_parquet()

@router.get("/variancia")
def endpoint_variancia(request: Request):
    colunas, filtros = parametros.preparar_parametros(request)

    try:
        resultado = dispersao.variancia(df, colunas, filtros)

        return {
            "colunas":colunas,
            "filtros":filtros,
            "resultado":resultado}
    
    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )


@router.get("/desvio")
def endpoint_desvio_padrao(request: Request):
    colunas,filtros = parametros.preparar_parametros(request)

    try:
        resultado = dispersao.desvio_padrao(df, colunas, filtros)

        return {
            "colunas":colunas,
            "filtros":filtros,
            "resultado":resultado
        }
    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        )
