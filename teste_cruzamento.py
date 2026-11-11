from app.services.loader import carregar_parquet, pessoas
import pandas as pd

df = carregar_parquet()

# Total de linhas com sexo e estado físico informados
registros_validos = df.dropna(
    subset=["sexo", "estado_fisico"]
)

# Seleciona pessoas únicas
df_pessoas = pessoas(df)

pessoas_validas = df_pessoas.dropna(
    subset=["sexo", "estado_fisico"]
)

print("Linhas válidas:", len(registros_validos))

print("Pessoas únicas válidas:", len(pessoas_validas))

print("\nTabulação por pessoas únicas:")

print(
    pd.crosstab(
        pessoas_validas["sexo"],
        pessoas_validas["estado_fisico"]
    )
)