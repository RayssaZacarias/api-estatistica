# bloco 1
from pathlib import Path

import pandas as pd

from app.services.loader import carregar_por_ano


BASE_DIR = Path(__file__).resolve().parents[3]
OUT_DIR = BASE_DIR / "data" / "processed" / "auditoria"

COLUNAS = [
    "id",
    "pesid",
    "id_veiculo",
    "causa_acidente",
    "tipo_acidente",
    "causa_principal",
    "mortos",
    "estado_fisico",
]

AUSENTES = {
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


def normalizar_texto(serie):
    """Uniformiza ausências sem alterar o arquivo original."""
    serie = serie.astype("string").str.strip()

    return serie.mask(
        serie.str.casefold().isin(AUSENTES)
    )


def auditar_ano(ano, df):
    """Realiza as quatro verificações do Bloco 1."""

    faltantes = set(COLUNAS) - set(df.columns)

    if faltantes:
        raise ValueError(
            f"Ano {ano}: colunas ausentes: {faltantes}"
        )

    dados = df[COLUNAS].copy()

    for coluna in COLUNAS:
        if coluna != "mortos":
            dados[coluna] = normalizar_texto(
                dados[coluna]
            )


    grupos = dados.groupby("id")

    acidentes = grupos.size().to_frame("linhas")

    acidentes["envolvidos"] = (
        grupos["pesid"].nunique()
    )

    acidentes["veiculos"] = (
        grupos["id_veiculo"].nunique()
    )

    acidentes["causas"] = (
        grupos["causa_acidente"].nunique()
    )

    acidentes["tipos"] = (
        grupos["tipo_acidente"].nunique()
    )

    acidentes["linhas_esperadas"] = (
        acidentes["envolvidos"]
        * acidentes["causas"]
        * acidentes["tipos"]
    )

    ausencias = pd.DataFrame(index=acidentes.index)

    for coluna in [
        "pesid",
        "causa_acidente",
        "tipo_acidente",
    ]:
        ausencias[coluna] = (
            dados[coluna]
            .isna()
            .groupby(dados["id"])
            .any()
        )

    avaliavel = (
        (acidentes["envolvidos"] > 0)
        & (acidentes["causas"] > 0)
        & (acidentes["tipos"] > 0)
        & ~ausencias.any(axis=1)
    )

    confere = (
        acidentes["linhas"]
        == acidentes["linhas_esperadas"]
    )

    acidentes["regra"] = "Não avaliável"

    acidentes.loc[
        avaliavel & confere, "regra"
    ] = "Confere"

    acidentes.loc[
        avaliavel & ~confere, "regra"
    ] = "Não confere"


    mortos = pd.to_numeric(
        df["mortos"]
        .astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )

    acidentes["soma_bruta_mortos"] = (
        mortos.groupby(dados["id"]).sum()
    )

    estado = (
        dados["estado_fisico"]
        .fillna("")
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.casefold()
    )

    obitos = dados.loc[
        estado.isin(["obito", "morto", "morta"])
        & dados["id"].notna()
        & dados["pesid"].notna(),
        ["id", "pesid"],
    ].drop_duplicates()

    obitos_por_acidente = (
        obitos.groupby("id").size()
    )

    acidentes["obitos_pessoas"] = (
        obitos_por_acidente.reindex(
            acidentes.index,
            fill_value=0,
        )
    )

    acidentes["diferenca_mortos"] = (
        acidentes["soma_bruta_mortos"]
        - acidentes["obitos_pessoas"]
    )

    principal = (
        dados["causa_principal"]
        .str.casefold()
        .eq("sim")
        .fillna(False)
    )

    causas_principais = (
        dados.loc[
            principal
            & dados["id"].notna()
            & dados["causa_acidente"].notna()
        ]
        .groupby("id")["causa_acidente"]
        .nunique()
    )

    acidentes["quantidade_causas_principais"] = (
        causas_principais.reindex(
            acidentes.index,
            fill_value=0,
        )
    )

    total_acidentes = len(acidentes)

    total_pessoas = (
        dados[["id", "pesid"]]
        .dropna()
        .drop_duplicates()
        .shape[0]
    )

    total_veiculos = (
        dados[["id", "id_veiculo"]]
        .dropna()
        .drop_duplicates()
        .shape[0]
    )

    resumo = {
        "ano": ano,
        "linhas": len(dados),
        "linhas_sem_id": int(
            dados["id"].isna().sum()
        ),
        "acidentes": total_acidentes,
        "pessoas": total_pessoas,
        "veiculos": total_veiculos,
        "linhas_por_acidente": round(
            len(dados) / total_acidentes, 2
        ) if total_acidentes else 0,

        "regra_confere": int(
            (acidentes["regra"] == "Confere").sum()
        ),
        "regra_nao_confere": int(
            (acidentes["regra"] == "Não confere").sum()
        ),
        "regra_nao_avaliavel": int(
            (acidentes["regra"] == "Não avaliável").sum()
        ),

        "soma_bruta_mortos": float(mortos.sum()),
        "obitos_pessoas": len(obitos),

        "causa_principal_unica": int(
            (
                acidentes["quantidade_causas_principais"]
                == 1
            ).sum()
        ),
        "sem_causa_principal": int(
            (
                acidentes["quantidade_causas_principais"]
                == 0
            ).sum()
        ),
        "multiplas_causas_principais": int(
            (
                acidentes["quantidade_causas_principais"]
                > 1
            ).sum()
        ),
    }

    acidentes.index.name = "id"
    acidentes.insert(0, "ano", ano)

    return resumo, acidentes.reset_index()


def gerar_auditoria_estrutura():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    resumos = []

    for ano, df in sorted(carregar_por_ano().items()):
        print(f"Auditando {ano}...")

        resumo, detalhes = auditar_ano(ano, df)

        resumos.append(resumo)

        detalhes.to_csv(
            OUT_DIR / f"estrutura_detalhes_{ano}.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig",
        )

        # Libera a referência ao DataFrame detalhado
        del detalhes

    tabela = pd.DataFrame(resumos)

    tabela.to_csv(
        OUT_DIR / "estrutura_resumo.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )

    return tabela


if __name__ == "__main__":
    resultado = gerar_auditoria_estrutura()
    print(resultado.to_string(index=False))
