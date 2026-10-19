import pandas as pd
from app.services import validacao
from app.services.loader import carregar_parquet

df = carregar_parquet()

filtros = {
    "id": None,
    "pesid": None,
    "data_inversa": None,
    "dia_semana": None,
    "horario": None,
    "uf": None,
    "br": None,
    "km": None,
    "municipio": None,
    "causa_principal": None,
    "causa_acidente": None,
    "ordem_tipo_acidente": None,
    "tipo_acidente": None,
    "classificacao_acidente": None,
    "fase_dia": None,
    "sentido_via": None,
    "condicao_metereologica": None,
    "tipo_pista": None,
    "tracado_via": None,
    "uso_solo": None,
    "id_veiculo": None,
    "tipo_veiculo": None,
    "marca": None,
    "ano_fabricacao_veiculo": None,
    "tipo_envolvido": None,
    "estado_fisico": None,
    "idade": None,
    "sexo": None,
    "ilesos": None,
    "feridos_leves": None,
    "feridos_graves": None,
    "mortos": None,
    "latitude": None,
    "longitude": None,
    "regional": None,
    "delegacia": None,
    "uop": None,
    "ano_arquivo": None
}


def frequencia_absoluta(df: pd.DataFrame,colunas: list[str],filtros: dict | None = None):
    
    df = validacao.aplicar_filtro(df,filtros)

    resultados = {}

    for coluna in colunas:

        validacao.validar_coluna(df,coluna)

        frequencias = (df[coluna].value_counts())

        resultados[coluna] = {
            "frequencias": {
                str(categoria): int(valor)
                for categoria, valor in frequencias.items()
            },

            "total_valido": int(
                frequencias.sum()
            )
        }

    return resultados


def frequencia_relativa(df: pd.DataFrame,colunas: list[str],filtros: dict | None = None):

    df = validacao.aplicar_filtro(df,filtros)

    resultados = {}

    for coluna in colunas:

        validacao.validar_coluna(df,coluna)

        frequencias = (
            df[coluna]
            .value_counts(normalize=True)
            .mul(100)
            .round(2)
        )

        resultados[coluna] = {
            "frequencias": {
                str(categoria): int(valor)
                for categoria, valor in frequencias.items()
            },

            "total_valido": int(
                frequencias.sum()
            )
        }

    return resultados


def frequencia_absoluta_acumulada(df: pd.DataFrame,colunas: list[str],filtros: dict | None = None):
    
    df = validacao.aplicar_filtro(df,filtros)

    resultados = {}

    for coluna in colunas:

        validacao.validar_coluna(df,coluna)

        frequencias = (
            df[coluna]
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
                frequencias.sum()
            )
        }

    return resultados


def frequencia_relativa_acumulada(df: pd.DataFrame,colunas: list[str],filtros: dict | None = None):
    
    
    df = validacao.aplicar_filtro(df,filtros)

    resultados = {}

    for coluna in colunas:

        validacao.validar_coluna(df,coluna)

        frequencias = (
            df[coluna]
            .value_counts(normalize=True)
            .sort_index()
            .cumsum()
            .mul(100)
            .round(2)
        )

        resultados[coluna] = {
            "frequencias": {
                str(categoria): int(valor)
                for categoria, valor in frequencias.items()
            },

            "total_valido": int(
                frequencias.sum()
            )
        }

    return resultados