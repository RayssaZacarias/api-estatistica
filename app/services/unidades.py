
import pandas as pd

from app.services import loader


# =========================================================
# CLASSIFICAÇÃO DAS VARIÁVEIS
# =========================================================

COLUNAS_PESSOAS = {
    "pesid",
    "idade",
    "sexo",
    "estado_fisico",
    "tipo_envolvido",
}

COLUNAS_VEICULOS = {
    "id_veiculo",
    "tipo_veiculo",
    "marca",
    "ano_fabricacao_veiculo",
}

COLUNAS_ACIDENTES = {
    "id",
    "data_inversa",
    "dia_semana",
    "horario",
    "uf",
    "br",
    "km",
    "municipio",
    "causa_principal",
    "classificacao_acidente",
    "fase_dia",
    "sentido_via",
    "condicao_metereologica",
    "tipo_pista",
    "tracado_via",
    "uso_solo",
    "latitude",
    "longitude",
    "regional",
    "delegacia",
    "uop",
    "ano_arquivo",
    "mes",
    "hora",
}

# Categorias que podem ter múltiplos valores por acidente
COLUNAS_MULTIPLAS = {
    "causa_acidente",
    "tipo_acidente",
    "ordem_tipo_acidente",
}

# Contagens obtidas a partir dos estados físicos
COLUNAS_RESUMO = {
    "ilesos",
    "feridos_leves",
    "feridos_graves",
    "mortos",
    "nao_classificados",
    "total_pessoas",
}


# =========================================================
# IDENTIFICAR UNIDADE
# =========================================================

def identificar_unidade(coluna: str) -> str:

    if coluna in COLUNAS_PESSOAS:
        return "pessoas"

    if coluna in COLUNAS_VEICULOS:
        return "veiculos"

    if coluna in COLUNAS_ACIDENTES:
        return "acidentes"

    if coluna in COLUNAS_MULTIPLAS:
        return "categorias_acidente"

    if coluna in COLUNAS_RESUMO:
        return "resumo_acidentes"

    raise ValueError(
        f"A coluna '{coluna}' não possui unidade "
        "de análise configurada."
    )


# =========================================================
# SELECIONAR DADOS
# =========================================================

def selecionar_base(
    df: pd.DataFrame,
    coluna: str,
    unidade: str | None = None
) -> pd.DataFrame:

    if unidade is None:
        unidade = identificar_unidade(coluna)

    if unidade == "pessoas":
        return loader.pessoas(df)

    if unidade == "veiculos":
        return loader.veiculos(df)

    if unidade == "acidentes":
        return loader.acidentes(df)

    if unidade == "resumo_acidentes":
        return loader.resumo_pessoas_por_acidente(df)

    if unidade == "categorias_acidente":

        if coluna not in COLUNAS_MULTIPLAS:
            raise ValueError(
                "Unidade incompatível com a coluna."
            )

        return (
            df.dropna(subset=[coluna])
              .drop_duplicates(
                  ["ano_arquivo", "id", coluna]
              )
        )

    raise ValueError(
        f"Unidade de análise inválida: {unidade}"
    )
