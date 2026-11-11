import pandas as pd
from app.services import validacao, unidades
from app.utils import conversao




def media(
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

        # Seleciona a unidade correta
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
                "e não permite calcular média."
            )

        # Calcula com a unidade selecionada
        valor = base[coluna].mean()

        resultados[coluna] = (
            conversao.converter_valor(valor)
            if pd.notna(valor)
            else None
        )

    return resultados


def moda(
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

        # Seleciona a unidade correta
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

        # Calcula a moda com a unidade selecionada
        valores = (
            base[coluna]
            .mode(dropna=True)
            .tolist()
        )

        resultados[coluna] = (
            conversao.converter_valor(valores)
        )

    return resultados


def mediana(
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

        # Seleciona a unidade correta
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
                "e não permite calcular mediana."
            )

        # Calcula com a unidade selecionada
        valor = base[coluna].median()

        resultados[coluna] = (
            conversao.converter_valor(valor)
            if pd.notna(valor)
            else None
        )

    return resultados


# ADICIONAR A MEDIA DA FREQUENCIA
