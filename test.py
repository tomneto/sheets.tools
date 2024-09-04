import ttkbootstrap as ttk
import os
from typing import Tuple
from icecream import ic

from prediction import get_values_and_names, Comparison


def load_test(entradas: ttk.Text = None, comprobantes: ttk.Text = None) -> Tuple[str, str]:
    income_fp = "./._entradas"
    comp_fp = "./._comprovantes"

    income_content: str
    comp_content: str

    if os.path.isfile(income_fp) and os.path.isfile(comp_fp):

        with open(income_fp, "r") as income_file:
            income_content = income_file.read()
            if comprobantes is not None and entradas is not None:
                entradas.delete(1.0, ttk.END)
                entradas.insert(1.0, income_content)

        with open(comp_fp, "r") as comp_fp:
            comp_content = comp_fp.read()
            if comprobantes is not None and entradas is not None:
                comprobantes.delete(1.0, ttk.END)
                comprobantes.insert(1.0, comp_content)

    return income_content, comp_content


def test_comparison():
    income_content, comp_content = load_test()

    income_file_line_count = len(income_content.split(sep='\n'))
    comp_file_line_count = len(comp_content.split(sep='\n'))
    ic(income_file_line_count, comp_file_line_count)

    df_comp = get_values_and_names(comp_content)
    df_income = get_values_and_names(income_content)

    sum_comp = df_comp['values'].sum()
    sum_income = df_income['values'].sum()
    ic(sum_comp, sum_income)

    comparison = Comparison(df_income=df_income, df_comp=df_comp)

    ic(comparison.similar_rows)
    ic(comparison.not_found)

    ic(comparison.copy_result())

test_comparison()