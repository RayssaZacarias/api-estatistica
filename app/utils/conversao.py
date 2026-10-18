import numpy as np
import pandas as pd


def converter_valor(valor):

    if pd.isna(valor):
        return None

    if isinstance(valor, np.generic):
        return valor.item()

    return valor