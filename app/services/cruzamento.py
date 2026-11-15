
import pandas as pd

from app.services import validacao
from app.services.loader import pessoas, resumo_pessoas_por_acidente, veiculos


def tabela_cruzada(
    df: pd.DataFrame,
    colunas: list[str],
    filtros: dict | None = None,
    unidade: str = "pessoas"
):

    # Verifica se foram informadas duas colunas
    if len(colunas) != 2:
        raise ValueError(
            "A tabulação cruzada exige exatamente duas colunas."
        )

    # Seleciona a unidade de análise
    if unidade == "pessoas":
        df = pessoas(df)

    elif unidade == "acidentes":
        df = resumo_pessoas_por_acidente(df)

    elif unidade == "veiculos":
        df = veiculos(df)

    else:
        raise ValueError(
            "Unidade inválida. Escolha: pessoas, acidentes ou veiculos."
        )

    # Aplica os filtros
    df = validacao.aplicar_filtro(
        df,
        filtros
    )

    # Valida as colunas
    for coluna in colunas:
        validacao.validar_coluna(
            df,
            coluna
        )

    coluna1 = colunas[0]
    coluna2 = colunas[1]

    # Total após selecionar a unidade e aplicar os filtros
    total_registros = len(df)

    # Exclui valores ausentes nas duas colunas analisadas
    df = df.dropna(
        subset=[coluna1, coluna2]
    )

    # Realiza a tabulação cruzada
    tabela = pd.crosstab(
        df[coluna1],
        df[coluna2]
    )

    # Organiza o resultado para JSON
    resultado = {}

    for categoria, linha in tabela.iterrows():

        resultado[str(categoria)] = {
            str(categoria_coluna): int(valor)
            for categoria_coluna, valor in linha.items()
        }

    return {
        "unidade": unidade,
        "tabela": resultado,
        "total_registros": int(total_registros),
        "total_valido": int(tabela.to_numpy().sum()),
        "total_ausente": int(total_registros - len(df))
    }
