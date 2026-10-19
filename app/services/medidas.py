import pandas as pd
from app.services import validacao
from app.utils import conversao

df = pd.read_parquet(
    "data/processed/acidentes_tratado.parquet"
)

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

def media(df: pd.DataFrame,colunas: list[str],filtros: dict | None = None):
    df = validacao.aplicar_filtro(df,filtros)
    resultados = {}
    for coluna in colunas:

        validacao.validar_coluna(df,coluna)
        
        resultados[coluna] = conversao.converter_valor(df[coluna].mean())

    return resultados


def moda(df: pd.DataFrame,colunas: list[str],filtros: dict | None = None):
    df = validacao.aplicar_filtro(df,filtros)

    resultados = {}
    for coluna in colunas:

        validacao.validar_coluna(df,coluna)

        resultados[coluna] = conversao.converter_valor(df[coluna].mode().tolist())

    return resultados


def mediana(df: pd.DataFrame,colunas: list[str],filtros: dict | None = None):
    df = validacao.aplicar_filtro(df,filtros)

    resultados = {}
    for coluna in colunas:

        validacao.validar_coluna(df,coluna)

        resultados[coluna] = conversao.converter_valor(df[coluna].median())

    return resultados

