# bloco 3
from pathlib import Path
import unicodedata

import pandas as pd

from app.services.loader import RAW_DIR, extrair_ano


# =========================================================
# CAMINHOS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[3]

OUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "auditoria"
    / "validade"
)

# Referência oficial a ser preenchida com dados do DNIT.
DNIT_FILE = (
    BASE_DIR
    / "data"
    / "referencias"
    / "dnit_km_por_br_uf.csv"
)


# =========================================================
# CRITÉRIOS DA AUDITORIA
# =========================================================

IDADE_MAXIMA = 120

ANO_MINIMO_FABRICACAO = 1950

# Caixa geográfica aproximada do Brasil.
# Serve para identificar registros suspeitos.
LAT_MIN = -34
LAT_MAX = 6

LON_MIN = -74
LON_MAX = -28

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

COLUNAS_NECESSARIAS = [
    "id",
    "pesid",
    "data_inversa",
    "idade",
    "ano_fabricacao_veiculo",
    "km",
    "br",
    "uf",
    "latitude",
    "longitude",
    "tipo_envolvido",
    "tipo_veiculo",
]

COLUNAS_EXEMPLOS = [
    "id",
    "pesid",
    "data_inversa",
    "uf",
    "br",
    "km",
    "idade",
    "ano_fabricacao_veiculo",
    "latitude",
    "longitude",
    "tipo_envolvido",
    "tipo_veiculo",
]


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def normalizar_texto(serie):
    """
    Padroniza textos apenas para comparação.

    Não altera o DataFrame original.
    """

    return (
        serie.astype("string")
        .str.strip()
        .str.casefold()
        .fillna("")
    )


def remover_acentos(serie):
    """
    Facilita comparações de categorias textuais.
    """

    return (
        serie.astype("string")
        .str.strip()
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.casefold()
        .fillna("")
    )


def identificar_ausentes(serie):
    """
    Identifica valores ausentes e vazios disfarçados.

    Não substitui os valores originais.
    """

    return (
        serie.isna()
        | normalizar_texto(serie).isin(AUSENTES)
    )


def converter_numero(serie):
    """
    Converte temporariamente para análise numérica.

    Exemplo:
        '123,5' -> 123.5

    Não altera o CSV original.
    """

    texto = (
        serie.astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(
        texto,
        errors="coerce"
    )


def normalizar_br(serie):
    """
    Padroniza somente a chave usada no agrupamento.

    Exemplos:
        BR-116 -> 116
        116.0  -> 116
        40     -> 040
    """

    texto = (
        normalizar_texto(serie)
        .str.replace(r"^br[-\s]*", "", regex=True)
        .str.replace(r"\.0+$", "", regex=True)
        .str.zfill(3)
    )

    return texto.where(
        ~identificar_ausentes(serie),
        "SEM BR"
    )


def dentro_brasil(latitude, longitude):
    """
    Verifica se as coordenadas estão dentro
    de uma caixa geográfica aproximada.
    """

    return (
        latitude.between(LAT_MIN, LAT_MAX)
        & longitude.between(LON_MIN, LON_MAX)
    ).fillna(False)


def detectar_erro_escala(latitude, longitude):
    """
    Verifica se coordenadas fora do Brasil
    passariam a ficar dentro da caixa geográfica
    após uma possível correção de escala.

    Apenas sinaliza suspeitas.
    """

    original_valida = dentro_brasil(
        latitude,
        longitude
    )

    suspeito = pd.Series(
        False,
        index=latitude.index
    )

    fatores = [
        (10, 10),
        (0.1, 0.1),
        (100, 100),
        (0.01, 0.01),
        (10, 1),
        (0.1, 1),
        (1, 10),
        (1, 0.1),
    ]

    for fator_lat, fator_lon in fatores:

        corrigida = dentro_brasil(
            latitude * fator_lat,
            longitude * fator_lon
        )

        suspeito = suspeito | corrigida

    return (
        suspeito
        & ~original_valida
        & latitude.notna()
        & longitude.notna()
        & ~(
            latitude.eq(0)
            & longitude.eq(0)
        )
    ).fillna(False)


def contar(mascara):
    """
    Conta ocorrências sem excluir registros da base.
    """

    return int(mascara.fillna(False).sum())


def contar_pessoas_identificadas(df, mascara):
    """
    Conta pessoas distintas com identificação disponível.

    Registros sem pesid continuam incluídos nas
    contagens por linha e são informados separadamente.
    """

    selecionados = df.loc[
        mascara.fillna(False),
        ["id", "pesid"]
    ]

    identificados = selecionados.loc[
        ~identificar_ausentes(selecionados["id"])
        & ~identificar_ausentes(selecionados["pesid"])
    ]

    return len(
        identificados.drop_duplicates()
    )


def coletar_exemplos(df, ano, nome, mascara, limite=10):
    """
    Retorna até 10 exemplos por problema.

    O limite vale apenas para o CSV de exemplos.
    As estatísticas consideram todas as linhas.
    """

    colunas = [
        coluna
        for coluna in COLUNAS_EXEMPLOS
        if coluna in df.columns
    ]

    exemplos = df.loc[
        mascara.fillna(False),
        colunas
    ].head(limite).copy()

    exemplos.insert(0, "problema", nome)
    exemplos.insert(0, "ano", ano)

    return exemplos


# =========================================================
# REFERÊNCIA DO DNIT
# =========================================================

def carregar_referencias_dnit():

    colunas = [
        "uf",
        "br",
        "km_final_oficial",
        "extensao_km_oficial",
        "fonte",
        "versao",
    ]

    if not DNIT_FILE.exists():

        print(
            "\nAviso: referência DNIT não encontrada."
            "\nA auditoria de km será executada,"
            "\nmas a comparação oficial ficará pendente.\n"
        )

        return pd.DataFrame(columns=colunas)

    dnit = pd.read_csv(
        DNIT_FILE,
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )

    faltantes = set(colunas) - set(dnit.columns)

    if faltantes:
        raise ValueError(
            f"Colunas faltantes no arquivo DNIT: {faltantes}"
        )

    dnit = dnit[colunas].copy()

    dnit["uf"] = (
        dnit["uf"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    dnit["br"] = normalizar_br(dnit["br"])

    for coluna in [
        "km_final_oficial",
        "extensao_km_oficial",
    ]:
        dnit[coluna] = converter_numero(
            dnit[coluna]
        )

    if dnit.duplicated(["uf", "br"]).any():
        raise ValueError(
            "Há referências duplicadas para a mesma BR e UF."
        )

    return dnit


# =========================================================
# AUDITORIA DE UM ANO
# =========================================================

def auditar_validade(ano, df, referencias_dnit):

    faltantes = (
        set(COLUNAS_NECESSARIAS)
        - set(df.columns)
    )

    if faltantes:
        raise ValueError(
            f"Ano {ano}: colunas ausentes: {faltantes}"
        )

    # Trabalhamos diretamente com os dados brutos.
    # Nenhuma linha é removida.

    idade = converter_numero(df["idade"])

    fabricacao = converter_numero(
        df["ano_fabricacao_veiculo"]
    )

    km = converter_numero(df["km"])

    latitude = converter_numero(df["latitude"])

    longitude = converter_numero(df["longitude"])

    exemplos = []

    # =====================================================
    # 1. IDADE
    # =====================================================

    idade_ausente = identificar_ausentes(
        df["idade"]
    )

    idade_nao_numerica = (
        ~idade_ausente
        & idade.isna()
    )

    idade_zero = idade.eq(0)

    idade_negativa = idade.lt(0)

    idade_acima_limite = idade.gt(
        IDADE_MAXIMA
    )

    idade_9xx = idade.between(
        900,
        999
    )

    idade_19xx = idade.between(
        1900,
        1999
    )

    idade_20xx = idade.between(
        2000,
        2099
    )

    mascaras_idade = {
        "Idade negativa": idade_negativa,
        "Idade acima de 120": idade_acima_limite,
        "Idade entre 900 e 999": idade_9xx,
        "Idade entre 1900 e 1999": idade_19xx,
        "Idade entre 2000 e 2099": idade_20xx,
    }

    for nome, mascara in mascaras_idade.items():

        exemplos.append(
            coletar_exemplos(
                df,
                ano,
                nome,
                mascara
            )
        )

    # =====================================================
    # 2. ANO DE FABRICAÇÃO
    # =====================================================

    # Primeiro tenta o formato usado pela PRF.
    datas = pd.to_datetime(
        df["data_inversa"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    # Também aceita datas no formato brasileiro.
    faltam_datas = datas.isna()

    if faltam_datas.any():

        datas.loc[faltam_datas] = pd.to_datetime(
            df.loc[faltam_datas, "data_inversa"],
            format="%d/%m/%Y",
            errors="coerce"
        )

    # Quando a data não puder ser lida, usa o ano
    # do arquivo como referência provisória.
    ano_acidente = datas.dt.year.fillna(ano)

    fabricacao_ausente = identificar_ausentes(
        df["ano_fabricacao_veiculo"]
    )

    fabricacao_zero = fabricacao.eq(0)

    fabricacao_antes_1950 = (
        fabricacao.gt(0)
        & fabricacao.lt(ANO_MINIMO_FABRICACAO)
    )

    fabricacao_futura = (
        fabricacao.gt(ano_acidente)
    )

    # Regra atualmente utilizada no loader:
    # ano_fabricacao > ano_arquivo + 1
    fabricacao_invalida_loader = (
        fabricacao.lt(1900)
        | fabricacao.gt(ano + 1)
    )

    exemplos.append(
        coletar_exemplos(
            df,
            ano,
            "Fabricação anterior a 1950",
            fabricacao_antes_1950
        )
    )

    exemplos.append(
        coletar_exemplos(
            df,
            ano,
            "Fabricação posterior ao acidente",
            fabricacao_futura
        )
    )

    # =====================================================
    # 3. QUILOMETRAGEM
    # =====================================================

    km_ausente = identificar_ausentes(
        df["km"]
    )

    km_nao_numerico = (
        ~km_ausente
        & km.isna()
    )

    km_zero = km.eq(0)

    km_negativo = km.lt(0)

    exemplos.append(
        coletar_exemplos(
            df,
            ano,
            "KM negativo",
            km_negativo
        )
    )

    # Agrupamento por BR e UF.
    # Todas as linhas permanecem na contagem.

    tabela_km = pd.DataFrame({
        "uf": (
            df["uf"]
            .astype("string")
            .str.strip()
            .str.upper()
        ),
        "br": normalizar_br(df["br"]),
        "km": km,
        "km_ausente": km_ausente,
        "km_nao_numerico": km_nao_numerico,
        "km_zero": km_zero,
        "km_negativo": km_negativo,
    })

    tabela_km["uf"] = tabela_km["uf"].where(
        ~identificar_ausentes(df["uf"]),
        "SEM UF"
    )

    km_por_br = (
        tabela_km
        .groupby(
            ["uf", "br"],
            dropna=False
        )
        .agg(
            registros=("km", "size"),
            km_ausentes=("km_ausente", "sum"),
            km_nao_numericos=("km_nao_numerico", "sum"),
            km_zeros=("km_zero", "sum"),
            km_negativos=("km_negativo", "sum"),
            km_maximo=("km", "max"),
        )
        .reset_index()
    )

    km_por_br.insert(0, "ano", ano)

    # Comparação com a referência oficial,
    # quando estiver disponível.

    km_por_br = km_por_br.merge(
        referencias_dnit,
        on=["uf", "br"],
        how="left",
        validate="many_to_one"
    )

    km_por_br["avaliacao_dnit"] = (
        "Sem referência DNIT"
    )

    avaliavel = (
        km_por_br["km_maximo"].notna()
        & km_por_br["km_final_oficial"].notna()
    )

    km_por_br.loc[
        avaliavel,
        "avaliacao_dnit"
    ] = "Dentro do marco final"

    km_por_br.loc[
        avaliavel
        & (
            km_por_br["km_maximo"]
            > km_por_br["km_final_oficial"]
        ),
        "avaliacao_dnit"
    ] = "Acima do marco final"

    # =====================================================
    # 4. COORDENADAS
    # =====================================================

    coordenadas_ausentes = (
        identificar_ausentes(df["latitude"])
        | identificar_ausentes(df["longitude"])
    )

    coordenadas_nao_numericas = (
        ~coordenadas_ausentes
        & (
            latitude.isna()
            | longitude.isna()
        )
    )

    coordenadas_numericas = (
        latitude.notna()
        & longitude.notna()
    )

    fora_limites_mundiais = (
        latitude.lt(-90)
        | latitude.gt(90)
        | longitude.lt(-180)
        | longitude.gt(180)
    )

    fora_brasil = (
        coordenadas_numericas
        & ~dentro_brasil(
            latitude,
            longitude
        )
    )

    coordenadas_zero = (
        latitude.eq(0)
        & longitude.eq(0)
    )

    erros_escala = detectar_erro_escala(
        latitude,
        longitude
    )

    mascaras_coordenadas = {
        "Fora dos limites mundiais":
            fora_limites_mundiais,

        "Fora da caixa geográfica do Brasil":
            fora_brasil,

        "Coordenadas 0,0":
            coordenadas_zero,

        "Possível erro de escala":
            erros_escala,
    }

    for nome, mascara in mascaras_coordenadas.items():

        exemplos.append(
            coletar_exemplos(
                df,
                ano,
                nome,
                mascara
            )
        )

    # =====================================================
    # 5. CONDUTORES MENORES DE 14 ANOS
    # =====================================================

    envolvido = remover_acentos(
        df["tipo_envolvido"]
    )

    veiculo = remover_acentos(
        df["tipo_veiculo"]
    )

    condutor = envolvido.str.contains(
        r"\bcondutor\b",
        regex=True,
        na=False
    )

    # Categorias consideradas motorizadas.
    # Lista auditável: pode ser ampliada conforme
    # o domínio observado no dicionário da PRF.

    padrao_motorizado = (
        r"automovel|"
        r"motocicleta|"
        r"motoneta|"
        r"ciclomotor|"
        r"caminhao|"
        r"caminhonete|"
        r"camioneta|"
        r"utilitario|"
        r"micro-onibus|"
        r"onibus|"
        r"trator|"
        r"quadriciclo|"
        r"triciclo|"
        r"motor-casa"
    )

    motorizado = veiculo.str.contains(
        padrao_motorizado,
        regex=True,
        na=False
    )

    condutor_menor_14 = (
        condutor
        & motorizado
        & idade.ge(0)
        & idade.lt(14)
    )

    # Identificar possíveis condutores menores de 14
    # com pesid ausente, sem descartá-los.

    pesid_ausente = identificar_ausentes(
        df["pesid"]
    )

    menor_sem_pesid = (
        condutor_menor_14
        & pesid_ausente
    )

    exemplos.append(
        coletar_exemplos(
            df,
            ano,
            "Condutor menor de 14 anos",
            condutor_menor_14
        )
    )

    # =====================================================
    # 6. RESUMO ANUAL
    # =====================================================

    resumo = {
        "ano": ano,
        "total_linhas": len(df),

        # IDADE
        "idade_ausente": contar(idade_ausente),
        "idade_nao_numerica": contar(
            idade_nao_numerica
        ),
        "idade_zero": contar(idade_zero),
        "idade_negativa": contar(
            idade_negativa
        ),
        "idade_acima_120": contar(
            idade_acima_limite
        ),
        "idade_9xx": contar(idade_9xx),
        "idade_19xx": contar(idade_19xx),
        "idade_20xx": contar(idade_20xx),

        # ANO DE FABRICAÇÃO
        "fabricacao_ausente": contar(
            fabricacao_ausente
        ),
        "fabricacao_zero": contar(
            fabricacao_zero
        ),
        "fabricacao_antes_1950": contar(
            fabricacao_antes_1950
        ),
        "fabricacao_futura": contar(
            fabricacao_futura
        ),
        "fabricacao_invalida_pelo_loader": contar(
            fabricacao_invalida_loader
        ),
        "data_acidente_invalida": contar(
            datas.isna()
        ),

        # KM
        "km_ausente": contar(km_ausente),
        "km_nao_numerico": contar(
            km_nao_numerico
        ),
        "km_zero": contar(km_zero),
        "km_negativo": contar(
            km_negativo
        ),

        # COORDENADAS
        "coordenadas_ausentes": contar(
            coordenadas_ausentes
        ),
        "coordenadas_nao_numericas": contar(
            coordenadas_nao_numericas
        ),
        "fora_limites_mundiais": contar(
            fora_limites_mundiais
        ),
        "fora_brasil": contar(fora_brasil),
        "coordenadas_0_0": contar(
            coordenadas_zero
        ),
        "possiveis_erros_escala": contar(
            erros_escala
        ),

        # CONDUTORES
        "condutores_menores_14_linhas": contar(
            condutor_menor_14
        ),
        "condutores_menores_14_pessoas_identificadas":
            contar_pessoas_identificadas(
                df,
                condutor_menor_14
            ),
        "condutores_menores_14_sem_pesid": contar(
            menor_sem_pesid
        ),
    }

    exemplos = pd.concat(
        exemplos,
        ignore_index=True
    )

    return resumo, km_por_br, exemplos


# =========================================================
# EXECUÇÃO GERAL
# =========================================================

def gerar_auditoria_validade():

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

    referencias_dnit = carregar_referencias_dnit()

    resumos = []
    tabelas_km = []
    tabelas_exemplos = []

    anos_processados = set()

    for caminho in arquivos:

        ano = extrair_ano(caminho)

        if ano in anos_processados:
            raise ValueError(
                f"Mais de um CSV encontrado para {ano}. "
                "Reúna os arquivos desse ano antes da auditoria."
            )

        anos_processados.add(ano)

        print(f"Auditando validade: {ano}")

        # Preserva inclusive os textos "NA", "null",
        # "Ignorado" e as células vazias.
        # Nenhum tratamento do loader é aplicado.

        df = pd.read_csv(
            caminho,
            sep=";",
            encoding="latin-1",
            dtype=str,
            low_memory=False,
            keep_default_na=False,
            na_filter=False,
        )

        resumo, km_por_br, exemplos = (
            auditar_validade(
                ano,
                df,
                referencias_dnit
            )
        )

        resumos.append(resumo)
        tabelas_km.append(km_por_br)
        tabelas_exemplos.append(exemplos)

        del df

    # =====================================================
    # CONSOLIDAÇÃO
    # =====================================================

    resumo_final = pd.DataFrame(
        resumos
    )

    km_final = pd.concat(
        tabelas_km,
        ignore_index=True
    )

    exemplos_final = pd.concat(
        tabelas_exemplos,
        ignore_index=True
    )

    # =====================================================
    # EXPORTAÇÃO — APENAS 3 CSVs
    # =====================================================

    arquivos_saida = {
        "validade_resumo.csv": resumo_final,
        "validade_km_por_br.csv": km_final,
        "validade_exemplos.csv": exemplos_final,
    }

    for nome, tabela in arquivos_saida.items():

        tabela.to_csv(
            OUT_DIR / nome,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

    print("\nAUDITORIA DO BLOCO 3 FINALIZADA")

    print(
        resumo_final.to_string(
            index=False
        )
    )

    return resumo_final


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    gerar_auditoria_validade()