"""
Visão do arquivo BRUTO: estatísticas calculadas direto sobre todas as linhas
dos CSVs, sem nenhum tratamento (sem deduplicar, sem filtrar, sem parquet).

Por ano: média/mediana da idade, média/mediana da idade da frota e número de óbitos.
Os arquivos são apenas LIDOS; nada é gravado neles.

Uso (a partir da raiz do projeto):
    python estatisticas_acidentes.py
    python estatisticas_acidentes.py caminho/da/pasta
Requer: pip install pandas
"""
import re
import sys
from pathlib import Path

import pandas as pd

pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/uploads")
arquivos = sorted(pasta.glob("acidentes20*_todas_caus*.csv"))
if not arquivos:
    sys.exit(f"Nenhum CSV acidentes20XX_todas_caus*.csv em {pasta.resolve()}")


def ler_csv(arq):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(arq, sep=None, engine="python", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não consegui decodificar {arq.name}")


def num(serie):
    if serie.dtype == object:
        serie = serie.astype(str).str.replace(",", ".", regex=False)
    return pd.to_numeric(serie, errors="coerce")


linhas = []
for arq in arquivos:
    ano = int(re.search(r"(20\d{2})", arq.name).group(1))
    df = ler_csv(arq)

    idade = num(df["idade"])
    frota = ano - num(df["ano_fabricacao_veiculo"])
    mortos = num(df["mortos"])
    # óbitos por acidente (soma de 'mortos' das linhas de cada acidente, sem tratamento)
    obitos_por_acidente = mortos.groupby(df["id"]).sum()

    linhas.append({
        "ano": ano,
        "linhas": len(df),
        "idade_media": idade.mean(),
        "idade_mediana": idade.median(),
        "idade_media_frota": frota.mean(),
        "idade_mediana_frota": frota.median(),
        "obitos": mortos.sum(),
        "obitos_media_por_acidente": obitos_por_acidente.mean(),
        "obitos_mediana_por_acidente": obitos_por_acidente.median(),
    })
    print(f"{arq.name}: {len(df)} linhas")

res = pd.DataFrame(linhas).set_index("ano")
print("\n=== Visão do arquivo bruto ===")
print(res.round(2).to_string())

print("\n=== Média e mediana do número de óbitos por ano (entre os anos) ===")
print(f"Média:   {res['obitos'].mean():.2f}")
print(f"Mediana: {res['obitos'].median():.2f}")

res.round(2).to_csv("resumo_bruto.csv", encoding="utf-8-sig")
print("\nSalvo em resumo_bruto.csv")