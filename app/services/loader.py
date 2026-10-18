import re
from pathlib import Path

import pandas as pd


# =========================================================
# CAMINHOS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "uploads"

OUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "acidentes_tratado.parquet"
)


# =========================================================
# VALORES QUE REPRESENTAM AUSÊNCIA DE INFORMAÇÃO
# =========================================================

PLACEHOLDERS = {
    "",
    "(null)",
    "null",
    "não informado",
    "nao informado",
    "ignorado",
    "(vazio)",
}


# =========================================================
# TIPOS DAS COLUNAS
# =========================================================

COLS_DECIMAIS = [
    "km",
    "latitude",
    "longitude",
]


COLS_INTEIRAS = [
    "idade",
    "ilesos",
    "feridos_leves",
    "feridos_graves",
    "mortos",
    "ano_fabricacao_veiculo",
    "ordem_tipo_acidente",
]


COLS_CONTAGEM = [
    "ilesos",
    "feridos_leves",
    "feridos_graves",
    "mortos",
]


# =========================================================
# LEITURA
# =========================================================

def ler_csv_bruto(path: Path) -> pd.DataFrame:
    """
    Lê um CSV sem alterar os dados originais.
    """

    return pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        dtype=str,
        low_memory=False
    )


def extrair_ano(path: Path) -> int:
    """
    Extrai o ano do nome do arquivo.

    Exemplo:
    acidentes2019_todas.csv -> 2019
    """

    resultado = re.search(r"(20\d{2})", path.name)

    if resultado is None:
        raise ValueError(
            f"Não foi possível encontrar o ano no arquivo: {path.name}"
        )

    return int(resultado.group(1))


def carregar_por_ano() -> dict[int, pd.DataFrame]:

    arquivos = sorted(RAW_DIR.glob("*.csv"))

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em {RAW_DIR}"
        )

    return {
        extrair_ano(path): ler_csv_bruto(path)
        for path in arquivos
    }


def carregar_bruto() -> pd.DataFrame:


    partes = []

    for ano, df in carregar_por_ano().items():

        parte = df.copy()

        parte["ano_arquivo"] = ano

        partes.append(parte)

    return pd.concat(
        partes,
        ignore_index=True
    )


# =========================================================
# NORMALIZAÇÃO DE VALORES VAZIOS
# =========================================================

def normalizar_vazios(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Transforma textos que significam ausência em pd.NA.

    Exemplo:

    "(null)"        -> NA
    "Não Informado" -> NA
    "Ignorado"      -> NA
    ""              -> NA
    """

    df = df.copy()

    colunas_texto = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for coluna in colunas_texto:

        serie = (
            df[coluna]
            .astype("string")
            .str.strip()
        )

        comparacao = serie.str.lower()

        serie = serie.mask(
            comparacao.isin(PLACEHOLDERS),
            pd.NA
        )

        df[coluna] = serie

    return df


# =========================================================
# CONVERSÃO NUMÉRICA
# =========================================================

def converter_decimais(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Converte colunas decimais.

    Exemplo:

    "123,5" -> 123.5

    Valores impossíveis de converter viram NaN.
    """

    df = df.copy()

    for coluna in COLS_DECIMAIS:

        if coluna not in df.columns:
            continue

        serie = (
            df[coluna]
            .astype("string")
            .str.replace(",", ".", regex=False)
        )

        df[coluna] = pd.to_numeric(
            serie,
            errors="coerce"
        )

    return df


def converter_inteiros(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Converte colunas que deveriam possuir valores inteiros.

    Valores não numéricos ou decimais indevidos viram NA.
    """

    df = df.copy()

    for coluna in COLS_INTEIRAS:

        if coluna not in df.columns:
            continue

        numeros = pd.to_numeric(
            df[coluna],
            errors="coerce"
        )

        # Exemplo:
        # idade = 20.5
        # não é uma idade inteira válida para essa base
        numeros = numeros.where(
            numeros.isna()
            | (numeros % 1 == 0)
        )

        df[coluna] = numeros.astype("Int64")

    return df


# =========================================================
# DATAS
# =========================================================

def tratar_datas(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Converte data e horário e cria:

    - mes
    - hora
    """

    df = df.copy()

    if "data_inversa" in df.columns:

        df["data_inversa"] = pd.to_datetime(
            df["data_inversa"],
            errors="coerce"
        )

        df["mes"] = (
            df["data_inversa"]
            .dt
            .month
            .astype("Int64")
        )

    if "horario" in df.columns:

        horario = pd.to_datetime(
            df["horario"],
            format="%H:%M:%S",
            errors="coerce"
        )

        df["hora"] = (
            horario
            .dt
            .hour
            .astype("Int64")
        )

    return df


# =========================================================
# VALIDAÇÕES
# =========================================================

def validar_idade(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Idades fora do intervalo permitido viram NA.

    0 é permitido porque pode existir bebê/criança
    envolvida no acidente.

    120 é um limite de segurança para evitar valores
    obviamente incorretos.
    """

    df = df.copy()

    if "idade" not in df.columns:
        return df

    invalido = (
        (df["idade"] < 0)
        | (df["idade"] > 120)
    )

    df.loc[
        invalido,
        "idade"
    ] = pd.NA

    return df


def validar_contagens(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Quantidades como mortos ou feridos
    não podem ser negativas.
    """

    df = df.copy()

    for coluna in COLS_CONTAGEM:

        if coluna not in df.columns:
            continue

        invalido = df[coluna] < 0

        df.loc[
            invalido,
            coluna
        ] = pd.NA

    return df


def validar_km(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    if "km" not in df.columns:
        return df

    # KM negativo não faz sentido.
    df.loc[
        df["km"] < 0,
        "km"
    ] = pd.NA

    return df


def validar_coordenadas(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    if "latitude" in df.columns:

        latitude_invalida = (
            (df["latitude"] < -90)
            | (df["latitude"] > 90)
        )

        df.loc[
            latitude_invalida,
            "latitude"
        ] = pd.NA

    if "longitude" in df.columns:

        longitude_invalida = (
            (df["longitude"] < -180)
            | (df["longitude"] > 180)
        )

        df.loc[
            longitude_invalida,
            "longitude"
        ] = pd.NA

    return df


def validar_ano_veiculo(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Remove anos de fabricação claramente impossíveis.

    O veículo não pode ser muito posterior
    ao ano do registro do acidente.
    """

    df = df.copy()

    if "ano_fabricacao_veiculo" not in df.columns:
        return df

    if "ano_arquivo" not in df.columns:
        return df

    invalido = (
        (df["ano_fabricacao_veiculo"] < 1900)
        |
        (
            df["ano_fabricacao_veiculo"]
            > df["ano_arquivo"] + 1
        )
    )

    df.loc[
        invalido,
        "ano_fabricacao_veiculo"
    ] = pd.NA

    return df


# =========================================================
# TRATAMENTO COMPLETO
# =========================================================

def tratar(
    df: pd.DataFrame,
    ano_arquivo: int
) -> pd.DataFrame:
    """
    Executa todo o tratamento necessário
    para deixar a base pronta para análise.
    """

    df = df.copy()

    df["ano_arquivo"] = ano_arquivo

    # 1. Padroniza ausências
    df = normalizar_vazios(df)

    # 2. Converte tipos
    df = converter_decimais(df)
    df = converter_inteiros(df)

    # 3. Datas
    df = tratar_datas(df)

    # 4. Regras de validade
    df = validar_idade(df)
    df = validar_contagens(df)
    df = validar_km(df)
    df = validar_coordenadas(df)
    df = validar_ano_veiculo(df)

    return df


# =========================================================
# CARREGAMENTO TRATADO
# =========================================================

def carregar_tratado() -> pd.DataFrame:
    """
    Carrega todos os CSVs e realiza o tratamento.
    """

    partes = []

    for ano, df in carregar_por_ano().items():

        parte = tratar(
            df,
            ano
        )

        partes.append(parte)

    return pd.concat(
        partes,
        ignore_index=True
    )


# =========================================================
# PARQUET
# =========================================================

def gerar_parquet():
    """
    Gera a versão tratada da base.

    Deve ser executado quando os CSVs
    forem alterados.
    """

    OUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df = carregar_tratado()

    df.to_parquet(
        OUT_FILE,
        index=False
    )

    print(
        f"Arquivo tratado salvo em: {OUT_FILE}"
    )


def carregar_parquet() -> pd.DataFrame:

    if not OUT_FILE.exists():

        raise FileNotFoundError(
            "O arquivo tratado ainda não existe. "
            "Execute gerar_parquet() primeiro."
        )

    return pd.read_parquet(
        OUT_FILE
    )


# =========================================================
# UNIDADES DE CONTAGEM
# =========================================================

def acidentes(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Uma linha por acidente.
    """

    return df.drop_duplicates(
        [
            "ano_arquivo",
            "id"
        ]
    )


def pessoas(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Uma linha por pessoa.
    """

    return (
        df
        .dropna(
            subset=["pesid"]
        )
        .drop_duplicates(
            [
                "ano_arquivo",
                "id",
                "pesid"
            ]
        )
    )


def veiculos(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Uma linha por veículo.
    """

    return (
        df
        .dropna(
            subset=["id_veiculo"]
        )
        .drop_duplicates(
            [
                "ano_arquivo",
                "id",
                "id_veiculo"
            ]
        )
    )


# =========================================================
# EXECUÇÃO MANUAL
# =========================================================

if __name__ == "__main__":

    import sys

    if "--gerar" in sys.argv:
        gerar_parquet()