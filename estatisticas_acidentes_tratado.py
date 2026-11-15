import sys
from pathlib import Path

import pandas as pd


PARQUET_PADRAO = Path("data/processed/acidentes_tratado.parquet")
SAIDA = Path("resumo_tratado.csv")

COLUNAS_NECESSARIAS = {
    "ano_arquivo", "id", "pesid", "id_veiculo", "idade",
    "ano_fabricacao_veiculo", "mortos",
}


def num(serie: pd.Series) -> pd.Series:
    """Converte valores numéricos sem mudar o arquivo de origem."""
    texto = serie.astype("string").str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce")


def calcular_estatisticas(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula métricas por ano, mantendo medidas por linha e por unidade."""
    faltantes = COLUNAS_NECESSARIAS - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltam colunas no Parquet: {', '.join(sorted(faltantes))}")

    anos = pd.to_numeric(df["ano_arquivo"], errors="coerce")
    sem_ano = int(anos.isna().sum())
    if sem_ano:
        print(f"AVISO: {sem_ano} linhas sem ano_arquivo válido não serão agrupadas por ano.")

    resultados = []
    for ano_num, grupo in df.loc[anos.notna()].groupby(anos.loc[anos.notna()], sort=True):
        ano = int(ano_num)
        print(f"Analisando {ano}: {len(grupo)} linhas tratadas")

        # ---------------------------------------------------------------
        # 1. MESMA METODOLOGIA DO SCRIPT BRUTO: cálculo em TODAS as linhas.
        # ---------------------------------------------------------------
        idade_linhas = num(grupo["idade"])
        idade_frota_linhas = ano - num(grupo["ano_fabricacao_veiculo"])
        mortos_linhas = num(grupo["mortos"])

        obitos_por_acidente_linhas = mortos_linhas.groupby(grupo["id"]).sum()

        # ---------------------------------------------------------------
        # 2. UNIDADE PESSOA: (id, pesid) única DENTRO de cada ano.
        #    Usa o primeiro valor NÃO NULO de idade e o maior indicador
        #    binário de morte encontrado entre linhas repetidas da pessoa.
        # ---------------------------------------------------------------
        base_pessoas = grupo.loc[
            grupo["id"].notna() & grupo["pesid"].notna(),
            ["id", "pesid", "idade", "mortos"],
        ].copy()
        base_pessoas["_idade"] = num(base_pessoas["idade"])
        base_pessoas["_obito"] = num(base_pessoas["mortos"]).eq(1).fillna(False)

        pessoas = (
            base_pessoas.groupby(["id", "pesid"], sort=False)
            .agg(idade=("_idade", "first"), obito=("_obito", "max"))
            .reset_index()
        )

        # ---------------------------------------------------------------
        # 3. UNIDADE VEÍCULO: (id, id_veiculo) única dentro do ano.
        # ---------------------------------------------------------------
        base_veiculos = grupo.loc[
            grupo["id"].notna() & grupo["id_veiculo"].notna(),
            ["id", "id_veiculo", "ano_fabricacao_veiculo"],
        ].copy()
        base_veiculos["_ano_fabricacao"] = num(base_veiculos["ano_fabricacao_veiculo"])

        veiculos = (
            base_veiculos.groupby(["id", "id_veiculo"], sort=False)
            .agg(ano_fabricacao=("_ano_fabricacao", "first"))
            .reset_index()
        )
        idade_frota_veiculos = ano - veiculos["ano_fabricacao"]

        # ---------------------------------------------------------------
        # 4. ÓBITOS POR ACIDENTE: conta pessoas únicas marcadas como mortas.
        #    Inclui acidentes sem pessoa identificada com contagem observada 0.
        #    Se faltar pesid, a contagem pode estar incompleta.
        # ---------------------------------------------------------------
        ids_acidentes = pd.Index(grupo["id"].dropna().unique())
        obitos_por_acidente_pessoas = (
            pessoas.groupby("id")["obito"].sum()
            .reindex(ids_acidentes, fill_value=0)
        )

        resultados.append({
            "ano": ano,
            "linhas": len(grupo),
            # Colunas equivalentes às do script de dados BRUTOS:
            "idade_media": idade_linhas.mean(),
            "idade_mediana": idade_linhas.median(),
            "idade_media_frota": idade_frota_linhas.mean(),
            "idade_mediana_frota": idade_frota_linhas.median(),
            "obitos": mortos_linhas.sum(),
            "obitos_media_por_acidente": obitos_por_acidente_linhas.mean(),
            "obitos_mediana_por_acidente": obitos_por_acidente_linhas.median(),
            # Medidas por unidade, sem repetir pessoa/veículo por causas/tipos:
            "acidentes_unicos": len(ids_acidentes),
            "pessoas_unicas": len(pessoas),
            "veiculos_unicos": len(veiculos),
            "idade_media_pessoas_unicas": pessoas["idade"].mean(),
            "idade_mediana_pessoas_unicas": pessoas["idade"].median(),
            "idade_media_frota_veiculos_unicos": idade_frota_veiculos.mean(),
            "idade_mediana_frota_veiculos_unicos": idade_frota_veiculos.median(),
            "obitos_pessoas_unicas": int(pessoas["obito"].sum()),
            "obitos_media_por_acidente_pessoas_unicas": obitos_por_acidente_pessoas.mean(),
            "obitos_mediana_por_acidente_pessoas_unicas": obitos_por_acidente_pessoas.median(),
            "linhas_sem_pesid": int(grupo["pesid"].isna().sum()),
            "linhas_sem_id_veiculo": int(grupo["id_veiculo"].isna().sum()),
        })

    if not resultados:
        raise ValueError("O Parquet não contém registros com ano_arquivo válido.")

    return pd.DataFrame(resultados).set_index("ano").sort_index()


def main() -> None:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else PARQUET_PADRAO
    if not caminho.is_file():
        sys.exit(f"Parquet tratado não encontrado: {caminho.resolve()}")

    df = pd.read_parquet(caminho)
    res = calcular_estatisticas(df)

    print("\n=== Estatísticas do Parquet tratado: mesmas contas do bruto ===")
    colunas_comparaveis = [
        "linhas", "idade_media", "idade_mediana", "idade_media_frota",
        "idade_mediana_frota", "obitos", "obitos_media_por_acidente",
        "obitos_mediana_por_acidente",
    ]
    print(res[colunas_comparaveis].round(2).to_string())

    print("\n=== Estatísticas do tratado por pessoa/veículo únicos ===")
    print(res[[
        "acidentes_unicos", "pessoas_unicas", "veiculos_unicos",
        "idade_media_pessoas_unicas", "idade_mediana_pessoas_unicas",
        "idade_media_frota_veiculos_unicos", "idade_mediana_frota_veiculos_unicos",
        "obitos_pessoas_unicas", "obitos_media_por_acidente_pessoas_unicas",
        "obitos_mediana_por_acidente_pessoas_unicas",
    ]].round(2).to_string())

    print("\n=== Óbitos por ano: média e mediana entre os anos (mesmo método do bruto) ===")
    print(f"Média:   {res['obitos'].mean():.2f}")
    print(f"Mediana: {res['obitos'].median():.2f}")

    res.round(2).to_csv(SAIDA, sep=";", decimal=",", encoding="utf-8-sig")
    print(f"\nCSV gerado: {SAIDA.resolve()}")


if __name__ == "__main__":
    main()