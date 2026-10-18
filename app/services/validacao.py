import pandas as pd


def validar_coluna(
    df: pd.DataFrame,
    coluna: str
):
    if coluna not in df.columns:
        raise ValueError(
            f"A coluna '{coluna}' não existe na base."
        )


def aplicar_filtro(
    df: pd.DataFrame,
    filtros: dict | None = None
):
    if filtros:

        for coluna_filtro, valor in filtros.items():

            if valor is not None:

                validar_coluna(
                    df,
                    coluna_filtro
                )

                tipo_coluna = df[coluna_filtro].dtype

                try:

                    if pd.api.types.is_integer_dtype(
                        tipo_coluna
                    ):
                        valor = int(valor)

                    elif pd.api.types.is_float_dtype(
                        tipo_coluna
                    ):
                        valor = float(
                            str(valor).replace(",", ".")
                        )

                    elif pd.api.types.is_datetime64_any_dtype(
                        tipo_coluna
                    ):
                        valor = pd.to_datetime(valor)

                except ValueError:
                    raise ValueError(
                        f"O valor '{valor}' não é válido "
                        f"para a coluna '{coluna_filtro}'."
                    )

                df = df[
                    df[coluna_filtro] == valor
                ]

    return df