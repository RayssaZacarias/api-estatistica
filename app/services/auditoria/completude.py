# bloco 2
from pathlib import Path

import pandas as pd

from app.services.loader import RAW_DIR, extrair_ano




BASE_DIR = Path(__file__).resolve().parents[3]

OUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "auditoria"
    / "completude_sintese"
)




CODIGOS_AUSENTES = {
    "",
    "na",
    "nan",
    "null",
    "(null)",
    "none",
    "não informado",
    "nao informado",
    "ignorado",
    "(vazio)",
    "na/na",
    "na/na/na",
}


ZERO_AUSENTE = {
    "ano_fabricacao_veiculo",
}




def identificar_ausencias(serie, coluna):
    """
    Identifica células fisicamente vazias e
    valores que representam ausência.

    Não modifica os dados originais.
    """

    original = (
        serie.astype("string")
        .fillna("")
    )

    # Células vazias ou contendo apenas espaços.
    vazios = original.str.strip().eq("")

    # Normalização temporária para comparação.
    texto = (
        original
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.casefold()
    )

    # Rótulos textuais de ausência.
    disfarcados = (
        texto.isin(CODIGOS_AUSENTES)
        & ~vazios
    )

    # Regra específica para ano de fabricação.
    if coluna in ZERO_AUSENTE:
        disfarcados = (
            disfarcados
            | texto.isin({"0", "0.0", "0,0"})
        )

    # Total de valores classificados como ausentes.
    ausentes = vazios | disfarcados

    return vazios, disfarcados, ausentes


def calcular_percentual(quantidade, total):

    if total == 0:
        return 0.0

    return round(
        quantidade / total * 100,
        2
    )




def auditar_ano(df, ano):
    """
    Analisa todas as linhas e colunas do CSV.

    Não remove duplicatas.
    Não exclui identificadores ausentes.
    Não aplica tratamentos.
    """

    total_linhas = len(df)
    total_colunas = len(df.columns)

    total_celulas = (
        total_linhas * total_colunas
    )

    celulas_vazias = 0
    celulas_disfarcadas = 0

    colunas_com_lacunas = 0
    colunas_totalmente_ausentes = 0

    linhas_com_ausencia = pd.Series(
        False,
        index=df.index
    )

    linhas_com_disfarcados = pd.Series(
        False,
        index=df.index
    )

    lacunas = []
    rotulos = []


    for coluna in df.columns:

        (
            vazios,
            disfarcados,
            ausentes,
        ) = identificar_ausencias(
            df[coluna],
            coluna
        )

        quantidade_vazios = int(
            vazios.sum()
        )

        quantidade_disfarcados = int(
            disfarcados.sum()
        )

        quantidade_ausentes = int(
            ausentes.sum()
        )

        # Acumula os totais de células.
        celulas_vazias += quantidade_vazios

        celulas_disfarcadas += quantidade_disfarcados

        # Identifica linhas com pelo menos
        # uma informação ausente.
        linhas_com_ausencia = (
            linhas_com_ausencia | ausentes
        )

        linhas_com_disfarcados = (
            linhas_com_disfarcados | disfarcados
        )

        if quantidade_ausentes > 0:
            colunas_com_lacunas += 1

        if (
            total_linhas > 0
            and quantidade_ausentes == total_linhas
        ):
            colunas_totalmente_ausentes += 1

        lacunas.append({
            "ano": ano,
            "variavel": coluna,
            "ausentes": quantidade_ausentes,
            "percentual": calcular_percentual(
                quantidade_ausentes,
                total_linhas
            ),
        })


        contagem_rotulos = (
            df.loc[disfarcados, coluna]
            .astype("string")
            .value_counts(dropna=False)
        )

        for rotulo, quantidade in contagem_rotulos.items():

            rotulos.append({
                "ano": ano,
                "variavel": coluna,
                "rotulo_original": str(rotulo),
                "quantidade": int(quantidade),
            })


    # Linhas excedentes em relação à primeira
    # ocorrência de cada registro idêntico.
    duplicatas_excedentes = int(
        df.duplicated(keep="first").sum()
    )

    # Todas as linhas pertencentes a grupos
    # com registros idênticos.
    linhas_em_grupos_duplicados = int(
        df.duplicated(keep=False).sum()
    )

    total_ausentes = (
        celulas_vazias
        + celulas_disfarcadas
    )

    resumo = {
        "ano": ano,

        "registros": total_linhas,
        "colunas": total_colunas,
        "total_celulas": total_celulas,

        "celulas_vazias": celulas_vazias,
        "celulas_disfarcadas": celulas_disfarcadas,
        "total_celulas_ausentes": total_ausentes,

        "percentual_ausencia": calcular_percentual(
            total_ausentes,
            total_celulas
        ),

        "linhas_com_ausencias": int(
            linhas_com_ausencia.sum()
        ),

        "linhas_com_vazios_disfarcados": int(
            linhas_com_disfarcados.sum()
        ),

        "colunas_com_lacunas": colunas_com_lacunas,

        "colunas_totalmente_ausentes": (
            colunas_totalmente_ausentes
        ),

        "duplicatas_excedentes": duplicatas_excedentes,

        "linhas_em_grupos_duplicados": (
            linhas_em_grupos_duplicados
        ),
    }

    return (
        resumo,
        pd.DataFrame(lacunas),
        pd.DataFrame(
            rotulos,
            columns=[
                "ano",
                "variavel",
                "rotulo_original",
                "quantidade",
            ],
        ),
    )



def montar_tabela_lacunas(df_lacunas):
    """
    Organiza cada variável em uma linha,
    mostrando ausências e percentuais por ano.
    """

    anos = sorted(
        df_lacunas["ano"].unique()
    )

    tabela = df_lacunas.pivot(
        index="variavel",
        columns="ano",
        values=["ausentes", "percentual"],
    )

    ordem_colunas = []

    for ano in anos:
        ordem_colunas.extend([
            ("ausentes", ano),
            ("percentual", ano),
        ])

    tabela = tabela.reindex(
        columns=pd.MultiIndex.from_tuples(
            ordem_colunas
        )
    )

    tabela.columns = [
        (
            f"{ano}_ausentes"
            if indicador == "ausentes"
            else f"{ano}_percentual"
        )
        for indicador, ano in tabela.columns
    ]

    return tabela.reset_index()


def gerar_auditoria_completude():

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    arquivos = sorted(
        RAW_DIR.glob("*.csv")
    )

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em {RAW_DIR}"
        )

    visoes_gerais = []
    todas_lacunas = []
    todos_rotulos = []

    anos_processados = set()

    for caminho in arquivos:

        ano = extrair_ano(caminho)

        if ano in anos_processados:
            raise ValueError(
                f"Mais de um CSV encontrado para {ano}"
            )

        anos_processados.add(ano)

        print(f"Auditando {ano}...")

        df = pd.read_csv(
            caminho,
            sep=";",
            encoding="latin-1",
            dtype=str,
            low_memory=False,
            keep_default_na=False,
            na_filter=False,
        )

        (
            resumo,
            lacunas,
            rotulos,
        ) = auditar_ano(df, ano)

        visoes_gerais.append(resumo)

        todas_lacunas.append(lacunas)

        todos_rotulos.append(rotulos)

        print(
            f"Registros: {resumo['registros']:,}"
        )

        print(
            f"Colunas: {resumo['colunas']}"
        )

        print(
            f"Células ausentes: "
            f"{resumo['total_celulas_ausentes']:,}"
        )

        print(
            f"Duplicatas exatas excedentes: "
            f"{resumo['duplicatas_excedentes']:,}"
        )

        # Libera o DataFrame original deste ano.
        del df

    visao_geral = pd.DataFrame(
        visoes_gerais
    ).sort_values("ano")

    lacunas_completas = pd.concat(
        todas_lacunas,
        ignore_index=True
    )

    lacunas_por_variavel = montar_tabela_lacunas(
        lacunas_completas
    )

    vazios_disfarcados = pd.concat(
        todos_rotulos,
        ignore_index=True
    )

    vazios_disfarcados = vazios_disfarcados.sort_values(
        ["ano", "variavel", "quantidade"],
        ascending=[True, True, False],
    )

    resultados = {
        "visao_geral.csv": visao_geral,
        "lacunas_por_variavel.csv": lacunas_por_variavel,
        "vazios_disfarcados.csv": vazios_disfarcados,
    }

    for nome, tabela in resultados.items():

        tabela.to_csv(
            OUT_DIR / nome,
            index=False,
            sep=";",
            encoding="utf-8-sig",
            decimal=",",
        )

    print("\nAUDITORIA FINALIZADA")

    print("Arquivos gerados:", len(resultados))

    return resultados


if __name__ == "__main__":
    gerar_auditoria_completude()
