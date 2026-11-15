import pandas as pd
from app.services import validacao, unidades
from app.utils import conversao


def variancia(
    df: pd.DataFrame,
    colunas: list[str],
    filtros: dict | None = None,
    unidade: str | None = None
):

    df = validacao.aplicar_filtro(
        df,
        filtros
    )

    resultados = {}

    for coluna in colunas:

        # Seleciona a unidade de análise
        base = unidades.selecionar_base(
            df,
            coluna,
            unidade
        )

        # Valida a existência da coluna
        validacao.validar_coluna(
            base,
            coluna
        )

        # Verifica se a variável é numérica
        if not pd.api.types.is_numeric_dtype(
            base[coluna]
        ):
            raise ValueError(
                f"A coluna '{coluna}' não é numérica "
                "e não permite calcular variância."
            )

        # Remove ausentes apenas do cálculo
        serie = base[coluna].dropna()

        if serie.empty:

            resultados[coluna] = None

            continue

        # Variância populacional
        valor = serie.var(ddof=0)

        resultados[coluna] = (
            conversao.converter_valor(valor)
            if pd.notna(valor)
            else None
        )

    return resultados

def desvio_padrao(
    df: pd.DataFrame,
    colunas: list[str],
    filtros: dict | None = None,
    unidade: str | None = None
):

    df = validacao.aplicar_filtro(
        df,
        filtros
    )

    resultados = {}

    for coluna in colunas:

        # Seleciona a unidade de análise
        base = unidades.selecionar_base(
            df,
            coluna,
            unidade
        )

        # Valida a existência da coluna
        validacao.validar_coluna(
            base,
            coluna
        )

        # Verifica se a variável é numérica
        if not pd.api.types.is_numeric_dtype(
            base[coluna]
        ):
            raise ValueError(
                f"A coluna '{coluna}' não é numérica "
                "e não permite calcular desvio padrão."
            )

        # Remove ausentes apenas do cálculo
        serie = base[coluna].dropna()

        if serie.empty:

            resultados[coluna] = None

            continue

        # Desvio padrão populacional
        valor = serie.std(ddof=0)

        resultados[coluna] = (
            conversao.converter_valor(valor)
            if pd.notna(valor)
            else None
        )

    return resultados