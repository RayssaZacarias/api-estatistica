#Bloco 4 
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


# Este arquivo deve ficar em app/services/auditoria/.
BASE_DIR = Path(__file__).resolve().parents[3]
RAW_DIR = BASE_DIR / "data" / "uploads"
OUT_DIR = BASE_DIR / "data" / "processed" / "auditoria"
REFERENCIA_UF_REGIONAL = BASE_DIR / "data" / "reference" / "uf_regional_validas.csv"

ANOS = range(2017, 2026)
COLUNAS = {
    "id", "pesid", "data_inversa", "dia_semana", "fase_dia", "horario",
    "classificacao_acidente", "estado_fisico", "ilesos", "feridos_leves",
    "feridos_graves", "mortos", "tipo_acidente", "tipo_envolvido",
    "br", "km", "sentido_via", "uf", "regional",
}
INDICADORES = ["ilesos", "feridos_leves", "feridos_graves", "mortos"]
AUSENCIAS = {"", "null", "(null)", "na", "n/a", "na/na", "na/na/na",
             "nao informado", "ignorado", "(vazio)", "nan", "none", "<na>"}

# Critérios aproximados, criados APENAS para triagem de possíveis divergências.
# Não representam horários astronômicos oficiais para todo o Brasil.
JANELAS_MINUTOS = {
    "amanhecer": (5 * 60, 7 * 60),       # 05:00–06:59
    "pleno dia": (7 * 60, 18 * 60),      # 07:00–17:59
    "anoitecer": (18 * 60, 20 * 60),     # 18:00–19:59
    "plena noite": (20 * 60, 5 * 60),    # 20:00–04:59 (vira o dia)
}

DIAS = {
    "segunda-feira": 0, "segunda": 0,
    "terca-feira": 1, "terca": 1,
    "quarta-feira": 2, "quarta": 2,
    "quinta-feira": 3, "quinta": 3,
    "sexta-feira": 4, "sexta": 4,
    "sabado": 5, "domingo": 6,
}
ESTADOS = {
    "ileso": "ilesos", "ilesa": "ilesos", "sem lesoes": "ilesos",
    "lesoes leves": "feridos_leves", "ferido leve": "feridos_leves",
    "lesao leve": "feridos_leves", "ferida leve": "feridos_leves",
    "lesoes graves": "feridos_graves", "ferido grave": "feridos_graves",
    "lesao grave": "feridos_graves", "ferida grave": "feridos_graves",
    "obito": "mortos", "morto": "mortos", "morta": "mortos",
}
CLASSES = {
    "sem vitimas": "sem_vitimas",
    "com vitimas feridas": "feridas",
    "com vitimas fatais": "fatais",
}


def normalizar(serie: pd.Series) -> pd.Series:
    """Padroniza acentos, maiúsculas e rótulos de ausência, sem excluir linhas."""
    valores = (serie.astype("string").str.strip().str.casefold()
               .str.normalize("NFKD").str.encode("ascii", errors="ignore")
               .str.decode("ascii"))
    return valores.mask(valores.isin(AUSENCIAS))


def ler_csv_bruto(caminho: Path) -> pd.DataFrame:
    """Seleciona só as colunas necessárias, mas mantém todos os registros."""
    df = pd.read_csv(
        caminho, sep=";", encoding="latin-1", dtype="string",
        keep_default_na=False, usecols=lambda coluna: coluna in COLUNAS,
    )
    if "id" not in df.columns:
        raise ValueError(f"Coluna obrigatória 'id' ausente: {caminho.name}")
    for coluna in COLUNAS - set(df.columns):
        df[coluna] = pd.NA
    return df


def carregar_referencia() -> pd.DataFrame | None:
    """Referência OPCIONAL: uf;regional;ano_inicio;ano_fim (período inclusivo).

    Nunca se presume que a sigla da regional precisa ser igual à UF.
    """
    if not REFERENCIA_UF_REGIONAL.exists():
        return None
    ref = pd.read_csv(REFERENCIA_UF_REGIONAL, sep=";", dtype="string")
    exigidas = {"uf", "regional", "ano_inicio", "ano_fim"}
    if not exigidas.issubset(ref.columns):
        raise ValueError(f"Referência precisa de: {sorted(exigidas)}")
    ref["uf"] = normalizar(ref["uf"])
    ref["regional"] = normalizar(ref["regional"])
    ref["ano_inicio"] = pd.to_numeric(ref["ano_inicio"], errors="coerce")
    ref["ano_fim"] = pd.to_numeric(ref["ano_fim"], errors="coerce")
    if ref[["uf", "regional", "ano_inicio", "ano_fim"]].isna().any().any():
        raise ValueError("Referência UF/regional tem campos vazios ou anos inválidos")
    return ref


def datas_prf(serie: pd.Series) -> pd.Series:
    """Datas ISO ou brasileiras (DD/MM/AAAA); inválidas ficam NaT."""
    iso = pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce")
    br = pd.to_datetime(serie, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(br)


def minutos_prf(serie: pd.Series) -> pd.Series:
    """Converte HH:MM ou HH:MM:SS em minutos; valores inválidos ficam NA."""
    extracao = serie.str.extract(r"^([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$")
    hora = pd.to_numeric(extracao[0], errors="coerce")
    minuto = pd.to_numeric(extracao[1], errors="coerce")
    return hora * 60 + minuto


def auditar_ano(
    ano: int, bruto: pd.DataFrame, referencia: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Retorna (resumo, ocorrências problemáticas, pares UF/regional).

    'consistente': passou na regra; 'inconsistente': violação lógica;
    'indicio': incompatibilidade com janela aproximada (requer confirmação);
    'nao_avaliavel': evidência insuficiente ou referência não fornecida.
    """
    df = bruto.copy()
    for coluna in COLUNAS - set(df.columns):
        df[coluna] = pd.NA
    for coluna in COLUNAS:
        df[coluna] = normalizar(df[coluna])

    # Sem ID, não há como atribuir as pessoas a um acidente. Preservamos esse
    # número no resumo, sem inventar identificadores de acidente.
    linhas_sem_id = int(df["id"].isna().sum())
    df = df.loc[df["id"].notna()].copy()

    registros_resumo: list[dict] = []
    registros_ocorrencias: list[pd.DataFrame] = []

    def registrar(
        nome: str, unidade: str, ids: pd.Series, status: pd.Series,
        explicacao: pd.Series, pesids: pd.Series | None = None,
        guardar_nao_avaliaveis: bool = True,
    ) -> None:
        # Usa valores posicionais para não alinhar acidentalmente índices repetidos.
        resultado = pd.DataFrame({
            "ano": ano, "teste": nome, "unidade": unidade,
            "id": ids.to_numpy(),
            "pesid": (pesids.to_numpy() if pesids is not None else pd.NA),
            "status": status.to_numpy(), "detalhe": explicacao.to_numpy(),
        })
        contagem = resultado["status"].value_counts()
        registros_resumo.append({
            "ano": ano, "teste": nome, "unidade": unidade,
            "total_avaliado": len(resultado),
            "consistentes": int(contagem.get("consistente", 0)),
            "inconsistentes": int(contagem.get("inconsistente", 0)),
            "indicios": int(contagem.get("indicio", 0)),
            "nao_avaliaveis": int(contagem.get("nao_avaliavel", 0)),
            "linhas_sem_id_fora_da_analise": linhas_sem_id,
        })
        problemas = resultado[resultado["status"] != "consistente"]
        if not guardar_nao_avaliaveis:
            problemas = problemas[problemas["status"] != "nao_avaliavel"]
        if not problemas.empty:
            registros_ocorrencias.append(problemas)

    # A estrutura 'todas as causas e tipos' repete atributos do acidente.
    # Valores diferentes para o MESMO acidente são conflito, não registros novos.
    g = df.groupby("id", sort=False)
    campos_acidente = [
        "data_inversa", "dia_semana", "fase_dia", "horario",
        "classificacao_acidente", "br", "km", "sentido_via", "uf", "regional",
    ]
    acc = g[campos_acidente].first()
    divergencias = g[campos_acidente].nunique(dropna=True).gt(1)
    ids_acidentes = pd.Series(acc.index, index=acc.index, dtype="string")

    # 1) DATA x DIA DA SEMANA
    datas = datas_prf(acc["data_inversa"])
    dia_declarado = acc["dia_semana"].map(DIAS)
    status = pd.Series("consistente", index=acc.index)
    status.loc[datas.isna() | dia_declarado.isna()] = "nao_avaliavel"
    status.loc[datas.notna() & dia_declarado.notna()
               & datas.dt.dayofweek.ne(dia_declarado)] = "inconsistente"
    status.loc[divergencias[["data_inversa", "dia_semana"]].any(axis=1)] = "inconsistente"
    motivo = pd.Series("Data e dia da semana compatíveis", index=acc.index)
    motivo.loc[status == "nao_avaliavel"] = "Data ausente/inválida ou dia não reconhecido"
    motivo.loc[status == "inconsistente"] = "Dia informado difere da data ou há valores contraditórios no acidente"
    registrar("data_x_dia_semana", "acidente", ids_acidentes, status, motivo)

    # 2) FASE x HORÁRIO (a divergência é somente INDÍCIO)
    minutos = minutos_prf(acc["horario"])
    fase = acc["fase_dia"]
    fase_reconhecida = fase.isin(JANELAS_MINUTOS)
    dentro = pd.Series(False, index=acc.index)
    for nome_fase, (inicio, fim) in JANELAS_MINUTOS.items():
        janela = ((minutos >= inicio) & (minutos < fim)) if inicio < fim else (
            (minutos >= inicio) | (minutos < fim))
        dentro |= fase.eq(nome_fase).fillna(False) & janela.fillna(False)
    status = pd.Series("consistente", index=acc.index)
    status.loc[minutos.isna() | ~fase_reconhecida] = "nao_avaliavel"
    status.loc[minutos.notna() & fase_reconhecida & ~dentro] = "indicio"
    status.loc[divergencias[["horario", "fase_dia"]].any(axis=1)] = "inconsistente"
    motivo = pd.Series("Dentro da janela aproximada", index=acc.index)
    motivo.loc[status == "nao_avaliavel"] = "Horário ausente/inválido ou fase não reconhecida"
    motivo.loc[status == "indicio"] = "Fora da janela aproximada: confirmar nascer/pôr do sol local"
    motivo.loc[status == "inconsistente"] = "Horário/fase conflitante entre linhas do mesmo acidente"
    registrar("fase_dia_x_horario", "acidente", ids_acidentes, status, motivo)

    # Pessoas únicas: mantém o primeiro valor NÃO NULO de cada campo, e conta
    # contradições em duplicatas de uma mesma pessoa.
    linhas_pessoas = df.dropna(subset=["pesid"])
    campos_pessoa = ["estado_fisico", "tipo_envolvido", *INDICADORES]
    if linhas_pessoas.empty:
        pessoas = pd.DataFrame(columns=["id", "pesid", *campos_pessoa])
        conflito_estado = pd.Series(dtype=bool)
        conflito_tipo = pd.Series(dtype=bool)
    else:
        gp = linhas_pessoas.groupby(["id", "pesid"], sort=False)
        pessoas = gp[campos_pessoa].first().reset_index()
        conflito_estado = gp[["estado_fisico", *INDICADORES]].nunique(dropna=True).gt(1).any(axis=1)
        conflito_tipo = gp["tipo_envolvido"].nunique(dropna=True).gt(1)
    pessoas["estado_tipo"] = pessoas["estado_fisico"].map(ESTADOS)
    pessoas["conflito_estado"] = conflito_estado.to_numpy(dtype=bool)
    pessoas["conflito_tipo"] = conflito_tipo.to_numpy(dtype=bool)

    # 3) ESTADO FÍSICO x indicadores binários, na unidade PESSOA.
    if not pessoas.empty:
        flags = pessoas[INDICADORES].apply(pd.to_numeric, errors="coerce")
        flags_completas = flags.notna().all(axis=1)
        flags_binarias = flags.isin([0, 1]).all(axis=1)
        soma = flags.sum(axis=1, min_count=4)
        marcada_correta = pd.Series(False, index=pessoas.index)
        for coluna in INDICADORES:
            marcada_correta |= (pessoas["estado_tipo"].eq(coluna) & flags[coluna].eq(1))
        status_p = pd.Series("consistente", index=pessoas.index)
        status_p.loc[pessoas["estado_tipo"].isna() | ~flags_completas] = "nao_avaliavel"
        status_p.loc[flags_completas & (
            ~flags_binarias | soma.ne(1) | ~marcada_correta
        )] = "inconsistente"
        status_p.loc[pessoas["conflito_estado"]] = "inconsistente"
        motivo_p = pd.Series("Estado corresponde ao único indicador igual a 1", index=pessoas.index)
        motivo_p.loc[status_p == "nao_avaliavel"] = "Estado desconhecido ou indicador ausente/inválido"
        motivo_p.loc[status_p == "inconsistente"] = "Estado/indicadores divergentes ou dados diferentes para o mesmo pesid"
        registrar("estado_fisico_x_indicadores", "pessoa", pessoas["id"],
                  status_p, motivo_p, pessoas["pesid"])
    else:
        registrar("estado_fisico_x_indicadores", "pessoa",
                  pd.Series(dtype="string"), pd.Series(dtype="string"), pd.Series(dtype="string"))

    # Agregações por acidente, após retirar duplicações de pessoas.
    if not pessoas.empty:
        p = pessoas.copy()
        p["mortes"] = p["estado_tipo"].eq("mortos")
        p["feridos"] = p["estado_tipo"].isin(["feridos_leves", "feridos_graves"])
        p["desconhecidos"] = p["estado_tipo"].isna() | p["conflito_estado"]
        p["pedestres"] = (p["tipo_envolvido"].str.contains(r"\bpedestre\b", na=False)
                          & ~p["conflito_tipo"])
        p["tipo_ausente"] = p["tipo_envolvido"].isna() | p["conflito_tipo"]
        ag_p = p.groupby("id").agg(
            qtd_pessoas=("pesid", "size"),
            mortes=("mortes", "sum"), feridos=("feridos", "sum"),
            desconhecidos=("desconhecidos", "sum"),
            pedestres=("pedestres", "sum"), tipo_ausente=("tipo_ausente", "sum"),
        )
    else:
        ag_p = pd.DataFrame()
    ag_p = ag_p.reindex(acc.index).fillna(0)
    for col in ["qtd_pessoas", "mortes", "feridos", "desconhecidos", "pedestres", "tipo_ausente"]:
        if col not in ag_p:
            ag_p[col] = 0
    linhas_sem_pesid = df["pesid"].isna().groupby(df["id"]).sum().reindex(acc.index).fillna(0)

    # 4) CLASSIFICAÇÃO x ESTADO FÍSICO DAS PESSOAS
    classe = acc["classificacao_acidente"].map(CLASSES)
    evid_fatal = ag_p["mortes"].gt(0)
    evid_ferido = ag_p["feridos"].gt(0)
    pendencias = (ag_p["desconhecidos"].gt(0) | linhas_sem_pesid.gt(0)
                  | ag_p["qtd_pessoas"].eq(0))
    incompat = ((classe.eq("sem_vitimas") & (evid_fatal | evid_ferido))
                | (classe.eq("feridas") & evid_fatal))
    confirmado = ((classe.eq("fatais") & evid_fatal)
                  | (classe.eq("feridas") & ~evid_fatal & evid_ferido & ~pendencias)
                  | (classe.eq("sem_vitimas") & ~evid_fatal & ~evid_ferido & ~pendencias))
    status = pd.Series("nao_avaliavel", index=acc.index)
    status.loc[confirmado.fillna(False)] = "consistente"
    status.loc[incompat.fillna(False)] = "inconsistente"
    # Quando toda a condição física é conhecida, ausência da gravidade exigida
    # também é uma contradição.
    status.loc[classe.notna() & ~pendencias & ~confirmado & ~incompat] = "inconsistente"
    status.loc[divergencias["classificacao_acidente"]] = "inconsistente"
    motivo = pd.Series("Faltam pessoas, estados físicos ou classificação confiável", index=acc.index)
    motivo.loc[status == "consistente"] = "Classificação compatível com a gravidade das pessoas"
    motivo.loc[status == "inconsistente"] = "Classificação incompatível com estados físicos ou valores contraditórios"
    registrar("classificacao_x_estado_fisico", "acidente", ids_acidentes, status, motivo)

    # 5) ATROPELAMENTO DE PEDESTRE x PRESENÇA DE PEDESTRE.
    # Verifica só acidentes com esse tipo, inclusive se ele aparece apenas em
    # uma das várias linhas de causas/tipos do mesmo acidente.
    tipo_alvo = df["tipo_acidente"].str.contains(r"atropelamento.*pedestre", na=False)
    ids_alvo = tipo_alvo.groupby(df["id"]).any().reindex(acc.index).fillna(False)
    alvo_idx = acc.index[ids_alvo]
    status = pd.Series("inconsistente", index=alvo_idx)
    presente = ag_p.loc[alvo_idx, "pedestres"].gt(0)
    informacao_incompleta = (ag_p.loc[alvo_idx, "tipo_ausente"].gt(0)
                            | linhas_sem_pesid.loc[alvo_idx].gt(0)
                            | ag_p.loc[alvo_idx, "qtd_pessoas"].eq(0))
    status.loc[informacao_incompleta] = "nao_avaliavel"
    status.loc[presente] = "consistente"
    motivo = pd.Series("Nenhum envolvido identificado como pedestre", index=alvo_idx)
    motivo.loc[status == "nao_avaliavel"] = "Informação de pessoas incompleta; ausência de pedestre não comprovada"
    motivo.loc[status == "consistente"] = "Há pedestre entre os envolvidos"
    registrar("atropelamento_x_pedestre", "acidente",
              pd.Series(alvo_idx, index=alvo_idx, dtype="string"), status, motivo)

    # 6) BR, KM e SENTIDO DA VIA AUSENTES AO MESMO TEMPO.
    # Detecta se houve ausência simultânea em QUALQUER linha do acidente.
    # Se outra linha estiver preenchida, ainda houve problema no registro bruto.
    ausentes_tres = (df[["br", "km", "sentido_via"]].isna().all(axis=1)
                     .groupby(df["id"]).any().reindex(acc.index).fillna(False))
    status = pd.Series("consistente", index=acc.index)
    status.loc[ausentes_tres] = "inconsistente"
    status.loc[divergencias[["br", "km", "sentido_via"]].any(axis=1)] = "inconsistente"
    motivo = pd.Series("Não há ausência simultânea dos três campos", index=acc.index)
    motivo.loc[ausentes_tres] = "BR, KM e sentido_via ausentes simultaneamente em pelo menos uma linha"
    motivo.loc[divergencias[["br", "km", "sentido_via"]].any(axis=1)] = (
        "Campos da via diferentes entre linhas do mesmo acidente")
    registrar("br_km_sentido_ausentes", "acidente", ids_acidentes, status, motivo)

    # 7) UF x REGIONAL: relatório descritivo SEM falso pressuposto UF == regional.
    pares = (acc[["uf", "regional"]].fillna("<ausente>")
             .value_counts(dropna=False).rename("quantidade_acidentes").reset_index())
    pares.insert(0, "ano", ano)
    status = pd.Series("nao_avaliavel", index=acc.index)
    motivo = pd.Series("Referência histórica UF/regional não fornecida", index=acc.index)
    if referencia is not None:
        ref_ano = referencia[(referencia["ano_inicio"] <= ano) & (referencia["ano_fim"] >= ano)]
        pares_validos = set(zip(ref_ano["uf"], ref_ano["regional"]))
        combinacoes = list(zip(acc["uf"], acc["regional"]))
        preenchidos = acc[["uf", "regional"]].notna().all(axis=1)
        compatibilidade = pd.Series([par in pares_validos for par in combinacoes], index=acc.index)
        status.loc[preenchidos & compatibilidade] = "consistente"
        status.loc[preenchidos & ~compatibilidade] = "inconsistente"
        motivo.loc[status == "consistente"] = "Par UF/regional consta da referência para o ano"
        motivo.loc[status == "inconsistente"] = "Par UF/regional não consta da referência fornecida"
        motivo.loc[status == "nao_avaliavel"] = "UF ou regional ausente"
    status.loc[divergencias[["uf", "regional"]].any(axis=1)] = "inconsistente"
    motivo.loc[divergencias[["uf", "regional"]].any(axis=1)] = "UF/regional conflitante no mesmo acidente"
    registrar("uf_x_regional", "acidente", ids_acidentes, status, motivo,
              guardar_nao_avaliaveis=referencia is not None)

    resumo = pd.DataFrame(registros_resumo)
    resumo["percentual_consistente_entre_avaliaveis"] = (
        100 * resumo["consistentes"]
        / (resumo["total_avaliado"] - resumo["nao_avaliaveis"]).replace(0, float("nan"))
    ).round(2)
    ocorrencias = (pd.concat(registros_ocorrencias, ignore_index=True)
                   if registros_ocorrencias else pd.DataFrame(
                       columns=["ano", "teste", "unidade", "id", "pesid", "status", "detalhe"]))
    return resumo, ocorrencias, pares


def executar() -> None:
    """Processa cada ano isoladamente e grava somente três CSVs consolidados."""
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Pasta de dados brutos não encontrada: {RAW_DIR}")

    arquivos: dict[int, Path] = {}
    for arquivo in sorted(RAW_DIR.glob("*.csv")):
        encontrado = re.search(r"(?<!\d)(201[7-9]|202[0-5])(?!\d)", arquivo.stem)
        if encontrado:
            ano = int(encontrado.group(1))
            if ano in arquivos:
                raise ValueError(
                    f"Mais de um CSV de {ano}. Mantenha somente a base 'todas as causas e tipos' "
                    f"para evitar misturar formatos: {arquivos[ano].name}; {arquivo.name}")
            arquivos[ano] = arquivo
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV de 2017 a 2025 em {RAW_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    destinos = {
        "resumo": OUT_DIR / "bloco4_resumo.csv",
        "ocorrencias": OUT_DIR / "bloco4_ocorrencias.csv",
        "pares": OUT_DIR / "bloco4_pares_uf_regional.csv",
    }
    referencia = carregar_referencia()
    primeira = True
    for ano in ANOS:
        if ano not in arquivos:
            print(f"[AVISO] Sem arquivo de {ano}; ano ignorado")
            continue
        print(f"[AUDITORIA] {ano}: {arquivos[ano].name}", flush=True)
        bruto = ler_csv_bruto(arquivos[ano])
        resumo, ocorrencias, pares = auditar_ano(ano, bruto, referencia)
        for nome, dados in [("resumo", resumo), ("ocorrencias", ocorrencias), ("pares", pares)]:
            dados.to_csv(destinos[nome], sep=";", index=False, encoding="utf-8-sig",
                         mode="w" if primeira else "a", header=primeira)
        primeira = False
        print(resumo[["teste", "consistentes", "inconsistentes", "indicios", "nao_avaliaveis"]]
              .to_string(index=False), flush=True)
    print(f"\nConcluído. Resultados em: {OUT_DIR}")
    if referencia is None:
        print("[ATENÇÃO] UF x regional: faltou referência histórica oficial. "
              "Os pares observados foram exportados; sem referência, os pares não foram "
              "rotulados automaticamente como erros.")


if __name__ == "__main__":
    executar()

