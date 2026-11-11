# bloco 5
import re
import unicodedata
from pathlib import Path

import pandas as pd

from app.services.loader import RAW_DIR, extrair_ano


BASE_DIR = Path(__file__).resolve().parents[3]
OUT_DIR = BASE_DIR / "data" / "processed" / "auditoria" / "padronizacao"
MAP_FILE = OUT_DIR / "equivalencia_causas.csv"
MAP_TIPOS_FILE = OUT_DIR / "equivalencia_tipos.csv"

COLUNAS_AUDITORIA = [
    "id", "causa_acidente", "tipo_acidente", "marca", "tracado_via",
    "uop", "uf", "municipio", "tipo_veiculo",
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

FABRICANTES_ALIAS = {
    "VW": "VOLKSWAGEN", "VOLKS": "VOLKSWAGEN", "VOLKSWAGEN": "VOLKSWAGEN",
    "GM": "CHEVROLET", "GM CHEVROLET": "CHEVROLET",
    "CHEVROLET": "CHEVROLET", "M BENZ": "MERCEDES-BENZ",
    "MERCEDES BENZ": "MERCEDES-BENZ", "MERCEDES": "MERCEDES-BENZ",
    "MMC": "MITSUBISHI", "MITSUBISHI": "MITSUBISHI",
    "FIAT": "FIAT", "FORD": "FORD", "RENAULT": "RENAULT",
    "HONDA": "HONDA", "TOYOTA": "TOYOTA", "HYUNDAI": "HYUNDAI",
    "NISSAN": "NISSAN", "PEUGEOT": "PEUGEOT", "CITROEN": "CITROEN",
    "LAND ROVER": "LAND ROVER", "JEEP": "JEEP", "VOLVO": "VOLVO",
    "SCANIA": "SCANIA", "IVECO": "IVECO", "KIA": "KIA",
}

# Grupos amplos sugeridos para comparação histórica; não são uma recodificação
# oficial e devem ser validados individualmente no arquivo de equivalência.
CATEGORIAS_SUGERIDAS = (
    "Condutor", "Pedestre", "Veículo", "Via", "Ambiente", "Outros"
)


def normalizar_nome(valor: str) -> str:
    valor = unicodedata.normalize("NFKD", str(valor).strip())
    valor = "".join(letra for letra in valor if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", valor.casefold()).strip()


def sugerir_categoria(nome: str) -> str:
    """Sugestão orientativa: não substitui a revisão metodológica."""
    if "pedestre" in nome:
        return "Pedestre"
    if any(t in nome for t in (
        "defeito mecanico", "falha mecanica", "pneu", "freio",
        "sistema de iluminacao do veiculo", "carga mal acondicionada"
    )):
        return "Veículo"
    if any(t in nome for t in (
        "defeito na via", "buraco", "sinalizacao da via", "acostamento",
        "obstrucao na via", "pista escorregadia"
    )):
        return "Via"
    if any(t in nome for t in (
        "chuva", "neblina", "cerração", "nevoeiro", "fenomenos da natureza",
        "condicoes climaticas", "vento forte"
    )):
        return "Ambiente"
    if any(t in nome for t in (
        "condutor", "velocidade", "ultrapassagem", "alcool", "drogas",
        "sono", "desatencao", "distancia de seguranca", "contramao",
        "manobra", "reacao tardia", "ausencia de reacao"
    )):
        return "Condutor"
    return "Revisar manualmente"


def sugerir_tipo(nome: str) -> str:
    """Agrupamentos candidatos; nomes similares não provam equivalência."""
    if nome.startswith("colisao lateral"):
        return "Colisão lateral (revisar sentidos)"
    if nome.startswith("colisao com objeto"):
        return "Colisão com objeto (revisar objeto)"
    if nome in {"danos eventuais", "eventos atipicos"}:
        return "Danos eventuais / Eventos atípicos (REVISAR)"
    return nome.title() if nome else "Revisar manualmente"


def ler_colunas_brutas(caminho: Path) -> pd.DataFrame:
    """Preserva literalmente os valores de origem, inclusive 'NA' e vazios."""
    return pd.read_csv(
        caminho,
        sep=";",
        encoding="latin-1",
        dtype=str,
        usecols=COLUNAS_AUDITORIA,
        keep_default_na=False,
        na_filter=False,
        low_memory=False,
    )


def levantar_causas_ano(ano: int, dados: pd.DataFrame) -> pd.DataFrame:
    """Conta linhas e acidentes distintos sem confundir pessoas com causas."""
    original = dados["causa_acidente"].astype("string").str.strip()
    ids = dados["id"].astype("string").str.strip()
    normalizado = original.map(normalizar_nome)

    valido = ~normalizado.isin(AUSENTES)
    base = pd.DataFrame({
        "id": ids,
        "causa_original": original,
    })
    base = base.loc[valido].copy()

    linhas = base.groupby("causa_original").size().rename("linhas_brutas")
    identificados = base.loc[base["id"].ne("") & ~base["id"].isna()]
    unicos = (
        identificados.drop_duplicates(["id", "causa_original"])
        .groupby("causa_original")
        .size()
        .rename("acidentes_com_causa")
    )

    tabela = pd.concat([linhas, unicos], axis=1).fillna(0).reset_index()
    tabela["linhas_brutas"] = tabela["linhas_brutas"].astype(int)
    tabela["acidentes_com_causa"] = tabela["acidentes_com_causa"].astype(int)
    total_acidentes = ids.loc[ids.notna() & ids.ne("")].nunique()
    tabela["total_acidentes_ano"] = int(total_acidentes)
    tabela["percentual_acidentes"] = (
        (tabela["acidentes_com_causa"] / total_acidentes * 100).round(2)
        if total_acidentes else 0.0
    )
    tabela.insert(0, "periodo", "2017-2020" if ano <= 2020 else "2021-2025")
    tabela.insert(0, "ano", ano)
    tabela["causa_normalizada"] = tabela["causa_original"].map(normalizar_nome)
    return tabela.sort_values(["acidentes_com_causa", "causa_original"], ascending=[False, True])


def levantar_tipos_ano(ano: int, dados: pd.DataFrame) -> pd.DataFrame:
    """Reutiliza a lógica de contagem por acidente para tipos múltiplos."""
    nomes = dados[["id", "tipo_acidente"]].rename(columns={"tipo_acidente": "causa_acidente"})
    inventario = levantar_causas_ano(ano, nomes)
    return inventario.rename(columns={
        "causa_original": "tipo_original",
        "causa_normalizada": "tipo_normalizado",
        "acidentes_com_causa": "acidentes_com_tipo",
    })


def propor_fabricante(marca: str) -> tuple[str, str]:
    """Propõe fabricante; não altera a descrição original da PRF."""
    texto = normalizar_nome(marca).upper()
    if normalizar_nome(marca) in AUSENTES:
        return "", "AUSENTE"
    partes = [p.strip() for p in texto.split("/") if p.strip()]
    if not partes:
        return "", "AUSENTE"
    if len(partes) > 1 and partes[0] in {"I", "IMP", "IMPORTADO", "N"}:
        partes = partes[1:]
    formato = "COM_BARRA" if "/" in texto else "SEM_BARRA"
    origem = re.sub(r"[^A-Z0-9 ]", " ", partes[0] if "/" in texto else texto)
    origem = re.sub(r"\s+", " ", origem).strip()
    for nome in sorted(FABRICANTES_ALIAS, key=len, reverse=True):
        if origem == nome or (formato == "SEM_BARRA" and origem.startswith(nome + " ")):
            return FABRICANTES_ALIAS[nome], formato + "_RECONHECIDO"
    return (origem.split(" ")[0] if origem else ""), formato + "_REVISAR"


def normalizar_tracado(valor: str) -> str:
    texto = normalizar_nome(valor)
    if texto in AUSENTES:
        return ""
    termos = [p.strip() for p in re.split(r"\s*[/,;|+]\s*", texto) if p.strip()]
    return " | ".join(sorted(set(termos)))


def mascara_uop(valor: str) -> str:
    """Descreve o formato observado; NÃO supõe um formato oficial válido."""
    if normalizar_nome(valor) in AUSENTES:
        return "AUSENTE"
    texto = unicodedata.normalize("NFKD", str(valor).strip().upper())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[A-Z]+", "A", re.sub(r"\d+", "9", texto))


def resumo_valores(ano: int, variavel: str, dados: pd.DataFrame,
                   funcao=None, regra: str = "") -> list[dict]:
    """Uma linha por rótulo distinto, mantendo sua frequência bruta."""
    resultados = []
    contagens = dados[variavel].astype(str).value_counts(dropna=False)
    for original, quantidade in contagens.items():
        equivalente = funcao(original) if funcao else normalizar_nome(original)
        resultados.append({
            "ano": ano, "variavel": variavel, "valor_original": original,
            "valor_proposto": equivalente,
            "quantidade_linhas": int(quantidade), "regra": regra,
        })
    return resultados


def analisar_padronizacao(ano: int, dados: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Audita sem filtrar linhas e sem transformar os valores de origem."""
    total = len(dados)
    detalhes = []

    # Marcas: avalia mudança de formato e grafias do mesmo fabricante.
    marcas = dados["marca"].astype(str)
    marcas_validas = ~marcas.map(lambda x: normalizar_nome(x) in AUSENTES)
    marcas_com_barra = marcas_validas & marcas.str.contains("/", regex=False)
    fabricantes_propostos = set()
    for original, quantidade in marcas.value_counts(dropna=False).items():
        fabricante, regra = propor_fabricante(original)
        if fabricante:
            fabricantes_propostos.add(fabricante)
        detalhes.append({"ano": ano, "variavel": "marca", "valor_original": original,
                         "valor_proposto": fabricante, "quantidade_linhas": int(quantidade),
                         "regra": regra})

    # Ordenação dos termos de 'tracado_via': mantém o rótulo original lado a lado.
    tracado = dados["tracado_via"].astype(str)
    tracados_originais = set()
    tracados_canonicos = set()
    for original, quantidade in tracado.value_counts(dropna=False).items():
        canonico = normalizar_tracado(original)
        if canonico:
            tracados_originais.add(original)
            tracados_canonicos.add(canonico)
        detalhes.append({"ano": ano, "variavel": "tracado_via", "valor_original": original,
                         "valor_proposto": canonico, "quantidade_linhas": int(quantidade),
                         "regra": "separar por / , ; | +; normalizar e ordenar termos"})

    # Códigos: identificadores não devem ser interpretados como float.
    ids = dados["id"].astype(str).str.strip()
    cientifico = ids.str.fullmatch(r"[+-]?\d+(?:[.,]\d+)?[Ee][+-]?\d+", na=False)
    id_nao_digito = ids.ne("") & ~ids.str.fullmatch(r"\d+", na=False)
    for original, quantidade in ids.loc[id_nao_digito].value_counts().items():
        detalhes.append({"ano": ano, "variavel": "id_formato_suspeito",
                         "valor_original": original, "valor_proposto": "",
                         "quantidade_linhas": int(quantidade),
                         "regra": "não converter ID para número; investigar na origem"})

    # UOP: é código da unidade operacional; sem dicionário não há validação oficial.
    uops = dados["uop"].astype(str)
    uops_validas = ~uops.map(lambda x: normalizar_nome(x) in AUSENTES)
    uops_suspeitas = (
        uops_validas & (uops.ne(uops.str.strip())
        | uops.str.contains(r"\s{2,}|[^\w\s./-]", regex=True))
    )
    for original, quantidade in uops.value_counts(dropna=False).items():
        detalhes.append({"ano": ano, "variavel": "uop",
                         "valor_original": original, "valor_proposto": mascara_uop(original),
                         "quantidade_linhas": int(quantidade),
                         "regra": "máscara: A=letras, 9=dígitos; conferir padrão oficial"})

    # Grafias de município: comparar dentro da mesma UF, sem renomear.
    municipios = dados["municipio"].astype(str)
    excesso_espaco = municipios.ne(municipios.str.strip()) | municipios.str.contains(r"\s{2,}", regex=True)
    pares_municipios = dados[["uf", "municipio"]].drop_duplicates().copy()
    pares_municipios["nome_normalizado"] = pares_municipios["municipio"].map(normalizar_nome)
    pares_municipios = pares_municipios.loc[~pares_municipios["nome_normalizado"].isin(AUSENTES)]
    grafias_multiplas = int((pares_municipios.groupby(["uf", "nome_normalizado"])
                            ["municipio"].nunique() > 1).sum())
    for (uf, original), quantidade in dados.groupby(["uf", "municipio"], dropna=False).size().items():
        detalhes.append({"ano": ano, "variavel": "municipio",
                         "valor_original": f"{uf} | {original}",
                         "valor_proposto": f"{normalizar_nome(uf)} | {normalizar_nome(original)}",
                         "quantidade_linhas": int(quantidade),
                         "regra": "apenas sugestão para análise de espaços e grafias por UF"})

    # Camioneta e caminhonete são classes legais diferentes; NÃO agrupar.
    tipos_veiculo = dados["tipo_veiculo"].astype(str)
    tipos_normalizados = tipos_veiculo.map(normalizar_nome)
    for original, quantidade in tipos_veiculo.value_counts(dropna=False).items():
        if "camioneta" in normalizar_nome(original) or "caminhonete" in normalizar_nome(original):
            detalhes.append({"ano": ano, "variavel": "tipo_veiculo",
                             "valor_original": original, "valor_proposto": original.strip(),
                             "quantidade_linhas": int(quantidade),
                             "regra": "rótulos semelhantes, mas tipos legais distintos: NÃO fundir"})

    return {
        "ano": ano, "total_linhas_brutas": int(total),
        "marca_preenchida": int(marcas_validas.sum()),
        "marca_com_barra": int(marcas_com_barra.sum()),
        "marca_sem_barra": int((marcas_validas & ~marcas_com_barra).sum()),
        "percentual_marca_com_barra": round(int(marcas_com_barra.sum()) / int(marcas_validas.sum()) * 100, 2)
        if marcas_validas.any() else 0.0,
        "fabricantes_propostos_distintos": len(fabricantes_propostos),
        "tracados_originais_distintos": len(tracados_originais),
        "tracados_ordenados_distintos": len(tracados_canonicos),
        "reducao_combinacoes_tracado": len(tracados_originais) - len(tracados_canonicos),
        "ids_ausentes": int(ids.map(lambda x: normalizar_nome(x) in AUSENTES).sum()),
        "ids_notacao_cientifica_linhas": int(cientifico.sum()),
        "ids_outros_formatos_suspeitos_linhas": int((id_nao_digito & ~cientifico).sum()),
        "uop_ausente_linhas": int((~uops_validas).sum()),
        "uop_formato_suspeito_linhas": int(uops_suspeitas.sum()),
        "uop_mascaras_distintas": int(uops.loc[uops_validas].map(mascara_uop).nunique()),
        "municipios_espacos_extras_linhas": int(excesso_espaco.sum()),
        "municipios_grafias_multiplas_por_uf": grafias_multiplas,
        "tipo_camioneta_linhas": int(tipos_normalizados.eq("camioneta").sum()),
        "tipo_caminhonete_linhas": int(tipos_normalizados.eq("caminhonete").sum()),
    }, detalhes


def gerar_modelo_equivalencia(inventario: pd.DataFrame) -> pd.DataFrame:
    saida = []
    for chave, grupo in inventario.groupby("causa_normalizada", sort=True):
        antigos = grupo.loc[grupo["ano"].le(2020), "acidentes_com_causa"].sum()
        novos = grupo.loc[grupo["ano"].ge(2021), "acidentes_com_causa"].sum()
        saida.append({
            "causa_normalizada": chave,
            "rotulos_originais": " | ".join(sorted(grupo["causa_original"].unique())),
            "anos_observados": ",".join(map(str, sorted(grupo["ano"].unique()))),
            "contagem_2017_2020": int(antigos),
            "contagem_2021_2025": int(novos),
            "categoria_sugerida": sugerir_categoria(chave),
            "categoria_comparavel": "",
            "status_revisao": "PENDENTE",
            "justificativa": "",
        })
    return pd.DataFrame(saida)


def gerar_modelo_tipos(inventario: pd.DataFrame) -> pd.DataFrame:
    saida = []
    for chave, grupo in inventario.groupby("tipo_normalizado", sort=True):
        antigos = grupo.loc[grupo["ano"].le(2020), "acidentes_com_tipo"].sum()
        novos = grupo.loc[grupo["ano"].ge(2021), "acidentes_com_tipo"].sum()
        saida.append({
            "tipo_normalizado": chave,
            "rotulos_originais": " | ".join(sorted(grupo["tipo_original"].unique())),
            "anos_observados": ",".join(map(str, sorted(grupo["ano"].unique()))),
            "contagem_2017_2020": int(antigos),
            "contagem_2021_2025": int(novos),
            "categoria_sugerida": sugerir_tipo(chave),
            "categoria_comparavel": "",
            "status_revisao": "PENDENTE",
            "justificativa": "",
        })
    return pd.DataFrame(saida)


def gerar_serie_harmonizada(arquivos: list[Path], mapa: pd.DataFrame,
                            coluna: str = "causa_acidente") -> pd.DataFrame:
    chave_mapa = "causa_normalizada" if coluna == "causa_acidente" else "tipo_normalizado"
    categorias = dict(zip(mapa[chave_mapa], mapa["categoria_comparavel"]))
    linhas = []
    for caminho in arquivos:
        ano = extrair_ano(caminho)
        dados = ler_colunas_brutas(caminho)
        causas = dados[coluna].astype("string").str.strip()
        chaves = causas.map(normalizar_nome)
        base = pd.DataFrame({
            "id": dados["id"].astype("string").str.strip(),
            "categoria": chaves.map(categorias),
        })
        total_acidentes = base.loc[base["id"].notna() & base["id"].ne(""), "id"].nunique()
        base = base.loc[
            base["id"].notna() & base["id"].ne("")
            & base["categoria"].notna() & base["categoria"].ne("")
        ]
        # Uma vez por acidente e categoria: duas causas específicas do mesmo
        # grupo não duplicam aquele acidente na categoria harmonizada.
        base = base.drop_duplicates(["id", "categoria"])
        contagens = base.groupby("categoria").size()
        for categoria, total in contagens.items():
            linhas.append({"ano": ano, "categoria_comparavel": categoria,
                          "acidentes_com_categoria": int(total),
                          "total_acidentes_ano": int(total_acidentes),
                          "percentual_acidentes": round(int(total) / total_acidentes * 100, 2)
                          if total_acidentes else 0.0})
    return pd.DataFrame(linhas).sort_values(["ano", "categoria_comparavel"])


def conferir_mapa_e_gerar_serie(arquivos: list[Path], modelo: pd.DataFrame,
                                caminho_mapa: Path, chave: str, coluna: str,
                                destino: str) -> None:
    """Mantém edições existentes; só gera série após conferência humana."""
    if not caminho_mapa.exists():
        modelo.to_csv(caminho_mapa, index=False, sep=";", encoding="utf-8-sig")
        print(f"Criado {caminho_mapa.name}: revisar e preencher categoria_comparavel.")
        return

    mapa = pd.read_csv(caminho_mapa, sep=";", encoding="utf-8-sig",
                       dtype=str, keep_default_na=False)
    if not {chave, "categoria_comparavel"}.issubset(mapa.columns):
        raise ValueError(f"{caminho_mapa.name} perdeu as colunas obrigatórias.")
    if mapa[chave].duplicated().any():
        raise ValueError(f"Categorias repetidas em {caminho_mapa.name}.")

    faltantes = set(modelo[chave]) - set(mapa[chave])
    pendentes = mapa["categoria_comparavel"].astype(str).str.strip().eq("")
    if faltantes or pendentes.any():
        print(f"{caminho_mapa.name}: {len(faltantes)} novos rótulos e "
              f"{int(pendentes.sum())} sem equivalência revisada. Série pendente.")
        # Em vez de sobrescrever o trabalho manual, documenta os novos itens.
        if faltantes:
            novos = modelo.loc[modelo[chave].isin(faltantes)]
            novos.to_csv(caminho_mapa.with_name("novos_" + caminho_mapa.name),
                         index=False, sep=";", encoding="utf-8-sig")
        return

    serie = gerar_serie_harmonizada(arquivos, mapa, coluna=coluna)
    serie.to_csv(OUT_DIR / destino, index=False, sep=";", encoding="utf-8-sig")
    print(f"Série comparável produzida em {destino}")


def gerar_auditoria_causas() -> pd.DataFrame:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(RAW_DIR.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV em {RAW_DIR}")

    anos = [extrair_ano(arquivo) for arquivo in arquivos]
    if len(anos) != len(set(anos)):
        raise ValueError("Mais de um CSV para algum ano: reúna os arquivos antes da auditoria.")

    inventarios = []
    inventarios_tipos = []
    resumos = []
    detalhes = []
    for arquivo, ano in zip(arquivos, anos):
        print(f"Auditando padrões e equivalências de {ano}...")
        dados = ler_colunas_brutas(arquivo)
        inventarios.append(levantar_causas_ano(ano, dados))
        inventarios_tipos.append(levantar_tipos_ano(ano, dados))
        resumo, linhas = analisar_padronizacao(ano, dados)
        resumos.append(resumo)
        detalhes.extend(linhas)
        del dados

    inventario = pd.concat(inventarios, ignore_index=True)
    inventario.to_csv(OUT_DIR / "causas_por_ano.csv", index=False,
                      sep=";", encoding="utf-8-sig")
    tipos = pd.concat(inventarios_tipos, ignore_index=True)
    tipos.to_csv(OUT_DIR / "tipos_por_ano.csv", index=False,
                 sep=";", encoding="utf-8-sig")
    pd.DataFrame(resumos).to_csv(OUT_DIR / "padronizacao_resumo.csv",
                                index=False, sep=";", encoding="utf-8-sig")
    pd.DataFrame(detalhes).to_csv(OUT_DIR / "padronizacao_valores.csv",
                                 index=False, sep=";", encoding="utf-8-sig")

    conferir_mapa_e_gerar_serie(
        arquivos, gerar_modelo_equivalencia(inventario), MAP_FILE,
        "causa_normalizada", "causa_acidente", "serie_harmonizada.csv",
    )
    conferir_mapa_e_gerar_serie(
        arquivos, gerar_modelo_tipos(tipos), MAP_TIPOS_FILE,
        "tipo_normalizado", "tipo_acidente", "serie_tipos_harmonizada.csv",
    )
    print("Auditoria concluída. Dados originais preservados.")
    return inventario


if __name__ == "__main__":
    gerar_auditoria_causas()