import pandas as pd
from app.services import validacao, unidades
from app.utils import conversao

def maximo(
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

        # Valida a coluna
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
                "e não permite calcular máximo numérico."
            )

        # Calcula usando a unidade correta
        valor = base[coluna].max()

        resultados[coluna] = (
            conversao.converter_valor(valor)
            if pd.notna(valor)
            else None
        )

    return resultados

def minimo(
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

        # Valida a coluna
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
                "e não permite calcular mínimo numérico."
            )

        # Calcula usando a unidade correta
        valor = base[coluna].min()

        resultados[coluna] = (
            conversao.converter_valor(valor)
            if pd.notna(valor)
            else None
        )

    return resultados


# =========================================================
# QUARTIS
# =========================================================

def quartis(
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

        # Valida a coluna
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
                "e não permite calcular quartis."
            )

        # Seleciona os valores válidos
        serie = base[coluna].dropna()

        # Caso não existam valores válidos
        if serie.empty:

            resultados[coluna] = {
                "Q1": None,
                "Q2": None,
                "Q3": None
            }

            continue

        # Calcula os quartis
        valores = serie.quantile([
            0.25,
            0.50,
            0.75
        ])

        resultados[coluna] = {
            "Q1": conversao.converter_valor(
                valores.loc[0.25]
            ),

            "Q2": conversao.converter_valor(
                valores.loc[0.50]
            ),

            "Q3": conversao.converter_valor(
                valores.loc[0.75]
            )
        }

    return resultados