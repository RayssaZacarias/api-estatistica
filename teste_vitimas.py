
import pandas as pd

from app.services.loader import carregar_parquet, pessoas

# 1. Carrega a base tratada
df_original = carregar_parquet()

# 2. Seleciona pessoas únicas identificadas
df = pessoas(df_original)

# 3. Verifica quantas pessoas não possuem estado físico
total_ausente = df["estado_fisico"].isna().sum()

# 4. Remove pessoas sem estado físico informado
df = df.dropna(
    subset=["estado_fisico"]
).copy()

# 5. Identifica as pessoas que morreram
df["mortos_calculado"] = (
    df["estado_fisico"] == "Óbito"
).fillna(False).astype(int)

# 6. Identifica pessoas com lesões graves
df["graves_calculado"] = (
    df["estado_fisico"] == "Lesões Graves"
).fillna(False).astype(int)

# 7. Soma mortos e feridos graves por acidente
df_acidentes = (
    df.groupby(["ano_arquivo", "id"])
    .agg(
        mortos=("mortos_calculado", "sum"),
        feridos_graves=("graves_calculado", "sum")
    )
    .reset_index()
)

# 8. Faz a tabulação cruzada
tabela = pd.crosstab(
    df_acidentes["mortos"],
    df_acidentes["feridos_graves"]
)

# 9. Exibe os resultados
print("\nTABELA CRUZADA:")
print(tabela.to_string())

print("\nTotal de acidentes analisados:")
print(len(df_acidentes))

print("\nPessoas sem estado físico informado:")
print(int(total_ausente))

print("\nTotal de mortos identificados:")
print(int(df_acidentes["mortos"].sum()))

print("\nTotal de feridos graves identificados:")
print(int(df_acidentes["feridos_graves"].sum()))

# 10. Verifica acidentes com mais de 10 mortos
print("\nACIDENTES COM MAIS DE 10 MORTOS:")

print(
    df_acidentes[
        df_acidentes["mortos"] > 10
    ].to_string(index=False)
)

# 11. Verifica acidentes com mais de 20 feridos graves
print("\nACIDENTES COM MAIS DE 20 FERIDOS GRAVES:")

print(
    df_acidentes[
        df_acidentes["feridos_graves"] > 20
    ].to_string(index=False)
)

# 12. Verifica os tipos de dados
print("\nTIPOS DAS COLUNAS:")

print(
    df_original[["ano_arquivo", "id"]].dtypes
)

# 13. Investiga o acidente de 2024 com ID 661121

# Converte os valores para números somente na comparação
filtro_ano = (
    pd.to_numeric(
        df_original["ano_arquivo"],
        errors="coerce"
    ) == 2024
)

filtro_id = (
    pd.to_numeric(
        df_original["id"],
        errors="coerce"
    ) == 661121
)

# Seleciona o acidente
acidente = df_original[
    filtro_ano & filtro_id
]

print("\nREGISTROS ORIGINAIS DO ACIDENTE:")
print(len(acidente))

# 14. Seleciona pessoas únicas identificadas
pessoas_acidente = pessoas(acidente)

print("\nPESSOAS ÚNICAS IDENTIFICADAS:")
print(len(pessoas_acidente))

# 15. Verifica a distribuição dos estados físicos
print("\nESTADO FÍSICO DAS PESSOAS:")

print(
    pessoas_acidente["estado_fisico"]
    .value_counts(dropna=False)
)

# 16. Confere especificamente mortos e feridos graves
print("\nMORTOS IDENTIFICADOS NO ACIDENTE:")
print(
    int(
        (pessoas_acidente["estado_fisico"] == "Óbito")
        .fillna(False)
        .sum()
    )
)

print("\nFERIDOS GRAVES IDENTIFICADOS NO ACIDENTE:")
print(
    int(
        (pessoas_acidente["estado_fisico"] == "Lesões Graves")
        .fillna(False)
        .sum()
    )
)

# 17. Verifica quantos registros foram removidos
print("\nREGISTROS REMOVIDOS:")

print(
    len(acidente) - len(pessoas_acidente)
)

# 18. Compara com o resultado da agregação
print("\nRESULTADO DO ACIDENTE NA TABELA AGREGADA:")

acidente_agregado = df_acidentes[
    (
        pd.to_numeric(
            df_acidentes["ano_arquivo"],
            errors="coerce"
        ) == 2024
    )
    &
    (
        pd.to_numeric(
            df_acidentes["id"],
            errors="coerce"
        ) == 661121
    )
]

print(
    acidente_agregado.to_string(index=False)
)
