import pandas as pd

from app.services import validacao, unidades




def frequencia_absoluta(
    df: pd.DataFrame,
    colunas: list[str],
    filtros: dict | None = None,
    unidade: str | None = None
):

    df = validacao.aplicar_filtro(df, filtros)

    resultados = {}

    for coluna in colunas:


        base = unidades.selecionar_base(
            df, coluna, unidade
        )

        validacao.validar_coluna(base, coluna)

    
        frequencias = (
            base[coluna]
            .value_counts()
        )

        resultados[coluna] = {
            "frequencias": {
                str(categoria): int(valor)
                for categoria, valor in frequencias.items()
            },

            "total_valido": int(
                base[coluna].notna().sum()
            )
        }

    return resultados



def frequencia_relativa(
    df: pd.DataFrame,
    colunas: list[str],
    filtros: dict | None = None,
    unidade: str | None = None
):

    df = validacao.aplicar_filtro(df, filtros)

    resultados = {}

    for coluna in colunas:

  
        base = unidades.selecionar_base(
            df, coluna, unidade
        )

        validacao.validar_coluna(base, coluna)


        frequencias = (
            base[coluna]
            .value_counts(normalize=True)
            .mul(100)
            .round(2)
        )

        resultados[coluna] = {
            "frequencias": {
                str(categoria): float(valor)
                for categoria, valor in frequencias.items()
            },

            "total_valido": int(
                base[coluna].notna().sum()
            )
        }

    return resultados




def frequencia_absoluta_acumulada(
    df: pd.DataFrame,
    colunas: list[str],
    filtros: dict | None = None,
    unidade: str | None = None
):

    df = validacao.aplicar_filtro(df, filtros)

    resultados = {}

    for coluna in colunas:


        base = unidades.selecionar_base(
            df, coluna, unidade
        )

        validacao.validar_coluna(base, coluna)

        frequencias = (
            base[coluna]
            .value_counts()
            .sort_index()
            .cumsum()
        )

        resultados[coluna] = {
            "frequencias": {
                str(categoria): int(valor)
                for categoria, valor in frequencias.items()
            },

            "total_valido": int(
                base[coluna].notna().sum()
            )
        }

    return resultados



def frequencia_relativa_acumulada(
    df: pd.DataFrame,
    colunas: list[str],
    filtros: dict | None = None,
    unidade: str | None = None
):

    df = validacao.aplicar_filtro(df, filtros)

    resultados = {}

    for coluna in colunas:

        base = unidades.selecionar_base(
            df, coluna, unidade
        )

        validacao.validar_coluna(base, coluna)

  
        frequencias = (
            base[coluna]
            .value_counts(normalize=True)
            .sort_index()
            .cumsum()
            .mul(100)
            .round(2)
        )

        resultados[coluna] = {
            "frequencias": {
                str(categoria): float(valor)
                for categoria, valor in frequencias.items()
            },

            "total_valido": int(
                base[coluna].notna().sum()
            )
        }

    return resultados