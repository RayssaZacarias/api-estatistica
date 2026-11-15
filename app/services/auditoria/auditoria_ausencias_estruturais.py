# bloco 2
import re
from collections import Counter
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = BASE_DIR / "data" / "uploads"
OUT_DIR = BASE_DIR / "data" / "processed" / "auditoria" / "completude"

# Apenas esses rótulos são tratados como ausência nesta auditoria.
# Inclusão de novos valores deve ser documentada e justificada.
ROTULOS_AUSENCIA = {
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

# Zero NÃO é ausência genérica: é válido em várias variáveis.
ZERO_COMO_AUSENCIA = {"ano_fabricacao_veiculo"}
COLUNAS_ESTRUTURA = ["id", "pesid", "tipo_veiculo", "idade", "tipo_envolvido"]
TAMANHO_BLOCO = 100_000


def mascara_ausente(serie: pd.Series, coluna: str) -> pd.Series:
    """Reconhece rótulos sem alterar os valores originais."""
    texto = serie.astype("string").fillna("").str.strip().str.casefold()
    mascara = texto.isin(ROTULOS_AUSENCIA)
    if coluna in ZERO_COMO_AUSENCIA:
        mascara |= texto.isin({"0", "0.0", "0,0"})
    return mascara


def identificador_valido(serie: pd.Series, coluna: str) -> pd.Series:
    """Preserva identificadores como texto, mas não contabiliza ausências."""
    return serie.astype("string").str.strip().mask(mascara_ausente(serie, coluna))


def arquivos_por_ano() -> dict[int, Path]:
    encontrados = {}
    for arquivo in RAW_DIR.glob("*.csv"):
        match = re.search(r"acidentes(20\d{2})", arquivo.name, flags=re.I)
        if not match:
            continue
        ano = int(match.group(1))
        if ano not in range(2017, 2026):
            continue
        if ano in encontrados:
            raise ValueError(f"Há dois arquivos para {ano}: {encontrados[ano]} e {arquivo}")
        encontrados[ano] = arquivo

    faltantes = sorted(set(range(2017, 2026)) - set(encontrados))
    if faltantes:
        raise FileNotFoundError(f"Faltam arquivos para os anos: {faltantes}. Pasta: {RAW_DIR}")
    return dict(sorted(encontrados.items()))


def analisar_ano(ano: int, arquivo: Path):
    """Lê um ano por blocos, produzindo evidências e contagens anuais."""
    contadores_rotulos = Counter()
    exemplos_rotulos = {}
    partes_estrutura = []
    variaveis = []
    n_linhas = 0

    leitor = pd.read_csv(
        arquivo, sep=";", encoding="latin-1", dtype=str,
        keep_default_na=False, na_filter=False,
        low_memory=False, chunksize=TAMANHO_BLOCO,
    )

    for lote in leitor:
        if not variaveis:
            variaveis = list(lote.columns)
            ausentes = sorted(set(COLUNAS_ESTRUTURA) - set(variaveis))
            if ausentes:
                raise ValueError(f"{ano}: colunas necessárias ausentes: {ausentes}")

        # Número da linha física do CSV, considerando o cabeçalho na linha 1.
        lote = lote.copy()
        lote["linha_csv"] = range(n_linhas + 2, n_linhas + len(lote) + 2)
        n_linhas += len(lote)

        partes_estrutura.append(lote[COLUNAS_ESTRUTURA + ["linha_csv"]].copy())

        # Identifica AUSÊNCIAS em TODAS as variáveis, não só nas 5 selecionadas.
        for coluna in variaveis:
            mascara = mascara_ausente(lote[coluna], coluna)
            if not mascara.any():
                continue

            valores_ausentes = lote.loc[mascara, coluna]
            for rotulo, quantidade in valores_ausentes.value_counts(dropna=False).items():
                rotulo = str(rotulo)
                chave = (coluna, rotulo)
                contadores_rotulos[chave] += int(quantidade)

                if chave not in exemplos_rotulos:
                    ocorrencia = lote.loc[mascara & lote[coluna].eq(rotulo)].iloc[0]
                    exemplos_rotulos[chave] = (
                        str(ocorrencia["id"]), int(ocorrencia["linha_csv"])
                    )

        del lote

    estrutura = pd.concat(partes_estrutura, ignore_index=True)
    del partes_estrutura

    # 1) Todos os rótulos de ausência efetivamente encontrados.
    rotulos = []
    for (coluna, rotulo), quantidade in sorted(contadores_rotulos.items()):
        id_exemplo, linha_exemplo = exemplos_rotulos[(coluna, rotulo)]
        rotulos.append({
            "ano": ano,
            "variavel": coluna,
            "rotulo_original": repr(rotulo) if not rotulo.strip() else rotulo,
            "quantidade_linhas": quantidade,
            "unidade": "linhas",
            "codigo_unico_proposto": "pd.NA",
            "regra": ("ano 0 tratado como ausência" if coluna in ZERO_COMO_AUSENCIA
                      and rotulo.strip() in {"0", "0.0", "0,0"}
                      else "rótulo de ausência reconhecido"),
            "exemplo_id": id_exemplo,
            "exemplo_linha_csv": linha_exemplo,
        })

    # 2) Total de ausências por variável, inclusive as que tiveram zero.
    ausencias_variaveis = []
    for coluna in variaveis:
        chaves = [chave for chave in contadores_rotulos if chave[0] == coluna]
        quantidade = sum(contadores_rotulos[chave] for chave in chaves)
        exemplo = exemplos_rotulos[chaves[0]] if chaves else ("", "")
        ausencias_variaveis.append({
            "ano": ano,
            "variavel": coluna,
            "unidade": "linhas",
            "total_linhas": n_linhas,
            "linhas_ausentes": quantidade,
            "percentual_ausente": round(100 * quantidade / n_linhas, 2) if n_linhas else 0,
            "regra": "rótulos explícitos de ausência; zero somente em ano_fabricacao_veiculo",
            "exemplo_id": exemplo[0],
            "exemplo_linha_csv": exemplo[1],
        })

    # 3) Linhas sem pesid, distribuídas por tipo_veiculo.
    estrutura["pesid_ausente"] = mascara_ausente(estrutura["pesid"], "pesid")
    tipo_veiculo = estrutura["tipo_veiculo"].astype("string").str.strip()
    tipo_veiculo = tipo_veiculo.str.replace(r"\s+", " ", regex=True)
    estrutura["tipo_veiculo_grupo"] = tipo_veiculo.mask(
        mascara_ausente(estrutura["tipo_veiculo"], "tipo_veiculo"), "[Ausente]"
    )

    sem_pesid_tipo = []
    for tipo, grupo in estrutura.groupby("tipo_veiculo_grupo", dropna=False, sort=True):
        sem = grupo.loc[grupo["pesid_ausente"]]
        exemplo = sem.iloc[0] if not sem.empty else None
        sem_pesid_tipo.append({
            "ano": ano,
            "tipo_veiculo": str(tipo),
            "unidade": "linhas",
            "total_linhas": len(grupo),
            "linhas_sem_pesid": len(sem),
            "percentual_sem_pesid": round(100 * len(sem) / len(grupo), 2),
            "regra": "pesid contém código de ausência",
            "exemplo_id": str(exemplo["id"]) if exemplo is not None else "",
            "exemplo_linha_csv": int(exemplo["linha_csv"]) if exemplo is not None else "",
        })

    # 4) Pessoas identificadas por (id, pesid), mesmo se surgirem em várias linhas.
    estrutura["id_valido"] = identificador_valido(estrutura["id"], "id")
    estrutura["pesid_valido"] = identificador_valido(estrutura["pesid"], "pesid")
    pessoas = estrutura.loc[
        estrutura["id_valido"].notna() & estrutura["pesid_valido"].notna(),
        ["id_valido", "pesid_valido", "idade", "tipo_envolvido", "linha_csv"],
    ].copy()
    pessoas["idade_ausente"] = mascara_ausente(pessoas["idade"], "idade")
    pessoas["tipo_tratado"] = pessoas["tipo_envolvido"].astype("string").str.strip().mask(
        mascara_ausente(pessoas["tipo_envolvido"], "tipo_envolvido")
    )

    identificadas = pessoas.groupby(["id_valido", "pesid_valido"], sort=False).agg(
        idade_ausente_todas=("idade_ausente", "all"),
        idade_ausente_alguma=("idade_ausente", "any"),
        tipo_envolvido=("tipo_tratado", "first"),
        quantidade_tipos=("tipo_tratado", "nunique"),
        exemplo_linha_csv=("linha_csv", "min"),
    ).reset_index()

    identificadas["tipo_envolvido"] = identificadas["tipo_envolvido"].fillna("[Ausente]")
    identificadas.loc[
        identificadas["quantidade_tipos"] > 1, "tipo_envolvido"
    ] = "[Múltiplos valores]"
    identificadas["idade_ausente_parcial"] = (
        identificadas["idade_ausente_alguma"]
        & ~identificadas["idade_ausente_todas"]
    )

    sem_idade_tipo = []
    for tipo, grupo in identificadas.groupby("tipo_envolvido", sort=True):
        sem = grupo.loc[grupo["idade_ausente_todas"]]
        exemplo = sem.iloc[0] if not sem.empty else None
        sem_idade_tipo.append({
            "ano": ano,
            "tipo_envolvido": str(tipo),
            "unidade": "pessoas distintas (id + pesid)",
            "total_pessoas": len(grupo),
            "pessoas_sem_idade": len(sem),
            "pessoas_idade_parcialmente_ausente": int(grupo["idade_ausente_parcial"].sum()),
            "percentual_sem_idade": round(100 * len(sem) / len(grupo), 2),
            "regra": "todas as linhas da pessoa têm idade ausente",
            "exemplo_id": str(exemplo["id_valido"]) if exemplo is not None else "",
            "exemplo_pesid": str(exemplo["pesid_valido"]) if exemplo is not None else "",
            "exemplo_linha_csv": int(exemplo["exemplo_linha_csv"]) if exemplo is not None else "",
        })

    resumo = {
        "ano": ano,
        "arquivo": arquivo.name,
        "total_linhas": n_linhas,
        "linhas_sem_pesid": int(estrutura["pesid_ausente"].sum()),
        "pessoas_identificadas": len(identificadas),
        "pessoas_sem_idade": int(identificadas["idade_ausente_todas"].sum()),
        "pessoas_idade_parcialmente_ausente": int(identificadas["idade_ausente_parcial"].sum()),
        "total_celulas_com_rotulo_ausente": sum(contadores_rotulos.values()),
    }

    return rotulos, ausencias_variaveis, sem_pesid_tipo, sem_idade_tipo, resumo


def gerar_auditoria():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    resultados = {
        "rotulos_ausencia.csv": [],
        "ausencias_por_variavel.csv": [],
        "sem_pesid_por_tipo_veiculo.csv": [],
        "sem_idade_por_tipo_envolvido.csv": [],
        "resumo_ano.csv": [],
    }
    for ano, arquivo in arquivos_por_ano().items():
        print(f"Auditando {ano}: {arquivo.name}")
        rotulos, variaveis, sem_pesid, sem_idade, resumo = analisar_ano(ano, arquivo)
        resultados["rotulos_ausencia.csv"].extend(rotulos)
        resultados["ausencias_por_variavel.csv"].extend(variaveis)
        resultados["sem_pesid_por_tipo_veiculo.csv"].extend(sem_pesid)
        resultados["sem_idade_por_tipo_envolvido.csv"].extend(sem_idade)
        resultados["resumo_ano.csv"].append(resumo)
        print(
            f"  {resumo['total_linhas']:,} linhas | "
            f"{resumo['linhas_sem_pesid']:,} linhas sem pesid | "
            f"{resumo['pessoas_sem_idade']:,} pessoas sem idade"
        )

    for nome, registros in resultados.items():
        pd.DataFrame(registros).to_csv(
            OUT_DIR / nome, sep=";", encoding="utf-8-sig", index=False
        )
        print(f"Gerado: {OUT_DIR / nome}")


if __name__ == "__main__":
    gerar_auditoria()



