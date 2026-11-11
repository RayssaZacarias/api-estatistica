
from fastapi import APIRouter, HTTPException, Request

from app.services.loader import carregar_parquet
from app.services import cruzamento
from app.utils.parametros import preparar_parametros


router = APIRouter()

df = carregar_parquet()


@router.get("/tabela")
def endpoint_tabela_cruzada(request: Request):

    colunas, filtros = preparar_parametros(request)

    # Retira a unidade dos filtros
    unidade = filtros.pop("unidade", "pessoas")

    try:
        resultado = cruzamento.tabela_cruzada(
            df,
            colunas,
            filtros,
            unidade
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
