import os
import re
import threading
import uuid
from enum import Enum
from tkinter import PhotoImage

import pandas as pd
import ttkbootstrap as ttk
import pyperclip
from icecream import ic
from test import load_test
from system import relative_path
from prediction import get_values_and_names, Comparison


class DesiredPattern(Enum):
    incoming: str = "incoming"
    outgoing: str = "outgoing"


def copy_from_treeview(tree, event):
    selection = tree.selection()
    result = ""
    for each in selection:
        try:
            value = f"""{",".join(tree.item(each)["values"])}\n"""
            result += value
        except:
            pass
    pyperclip.copy(result)


class MainWindow:
    df_comp: pd.DataFrame
    df_income: pd.DataFrame
    
    df_found: pd.DataFrame

    df_not_found_comp: pd.DataFrame
    df_not_found_income: pd.DataFrame

    not_found_count: int = 0

    threads: dict = {'submit': []}
    conversion_type: str = "Entradas"

    comparison: Comparison

    sum_comp: int = 0
    sum_income: int = 0

    class Colors:
        comp_not_found = "#a83232"
        income_not_found = "#8c7f00"

    def __init__(self):

        self.root = ttk.Window(themename="darkly", iconphoto=relative_path('icon.png'))
        img = PhotoImage(file=relative_path('icon.png'))
        self.root.iconbitmap(relative_path('icon.ico'))
        self.root.iconphoto(False, img)
        self.root.title("Diferença em Comprovantes e Entradas")

        # Comprobantes Entry
        comp_label = ttk.Label(self.root, text="Comprovantes:")
        comp_label.grid(row=0, column=0, sticky="w")

        self.comp_entry = ttk.Text(self.root, height=5, width=40)
        self.comp_entry.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Entradas Entry
        income_label = ttk.Label(self.root, text="Entradas:")
        income_label.grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.income_entry = ttk.Text(self.root, height=5, width=40)
        self.income_entry.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

        load_test(self.income_entry, self.comp_entry)

        # Submit Button
        submit_button = ttk.Button(self.root, text="Comparar", command=self.compare_income_comp)
        submit_button.grid(row=4, column=0, pady=(10, 0))

        convert_button_income = ttk.Button(self.root, text="Converter Entradas", command=self.convert_statement_to_table)
        convert_button_income.grid(row=5, column=0, pady=(10, 0))
        
        convert_button_outgoing = ttk.Button(self.root, text="Converter Saidas", command=lambda: self.convert_statement_to_table(DesiredPattern.outgoing))
        convert_button_outgoing.grid(row=6, column=0, pady=(10, 0))

        # Submit Button
        copy_result = ttk.Button(self.root, text="Copiar Resultado", command=self.copy_result)
        copy_result.grid(row=7, column=0, pady=(10, 0))

        # Similar Result Treeview
        found_label = ttk.Label(self.root, text="Encontrados:")
        found_label.grid(row=0, column=1, sticky="w")

        self.found_tree = ttk.Treeview(self.root, columns=('values', 'names', "origin"), show='headings')
        self.found_tree.bind("<Control-c>", lambda x: copy_from_treeview(self.found_tree, x))
        self.found_tree.bind("<Command-c>", lambda x: copy_from_treeview(self.found_tree, x))
        self.found_tree.heading('values', text='Valor')
        self.found_tree.heading('names', text='Nome')
        self.found_tree.heading('origin', text='Fonte')
        self.found_tree.grid(row=1, column=1, rowspan=4, padx=5, pady=5, sticky="nsew")

        # Not Found Treeview
        not_found_label = ttk.Label(self.root, text="Não Encontrados:")
        not_found_label.grid(row=0, column=2, sticky="w")

        self.not_found_tree = ttk.Treeview(self.root, columns=('values', 'names', "origin"), show='headings')
        self.not_found_tree.bind("<Control-c>", lambda x: copy_from_treeview(self.not_found_tree, x))
        self.not_found_tree.bind("<Command-c>", lambda x: copy_from_treeview(self.not_found_tree, x))

        self.not_found_tree.heading('values', text='Valor')
        self.not_found_tree.heading('names', text='Nome')
        self.not_found_tree.heading('origin', text='Fonte')
        self.not_found_tree.tag_configure('comprobantes', background=self.Colors.comp_not_found)
        self.not_found_tree.tag_configure('entradas', background=self.Colors.income_not_found)
        self.not_found_tree.grid(row=1, column=2, rowspan=4, padx=5, pady=5, sticky="nsew")

        # Result Label for Length
        self.result_label = ttk.Label(self.root, text="")
        self.result_label.grid(row=5, column=0, columnspan=3, pady=(10, 0))

        # Label for Sum of values
        self.sum_label = ttk.Label(self.root, text="")
        self.sum_label.grid(row=6, column=0, columnspan=3, pady=(5, 10))

        # Configure resizing behavior
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(3, weight=1)

        self.root.mainloop()

    def on_submit(self, comp_text: list, income_text: list):

        self.df_comp = get_values_and_names(comp_text)
        self.df_income = get_values_and_names(income_text)

        self.sum_comp = self.df_comp['values'].sum()
        self.sum_income = self.df_income['values'].sum()

        self.comparison = Comparison(df_income=self.df_income, df_comp=self.df_comp)

    def compare_income_comp(self, ):

        comp_text = self.comp_entry.get("1.0", "end-1c").split('\n')
        income_text = self.income_entry.get("1.0", "end-1c").split('\n')

        self.threads['submit'].append(threading.Thread(target=self.on_submit, args=(comp_text, income_text)))

        def run_in_bg():
            for idx, thr in enumerate(self.threads['submit']):
                del self.threads['submit'][idx]
                thr.start()
                thr.join()

                self.sum_label.config(text=f"Total em Comprovantes: {float(self.sum_comp):.2f} | Total em Entradas: {float(self.sum_income):.2f}\nTotal de diferença: {float(self.sum_comp - self.sum_income):.2f}")

                # Update the Treeview with the similar result
                for child in self.found_tree.get_children():
                    self.found_tree.delete(child)

                try:
                    for index, row in self.comparison.result.df_found.iterrows():
                        if row['origin'] == "comprobantes":
                            self.found_tree.insert('', ttk.END, values=(row['values'], row['names'], row['origin']))
                except:
                    pass

                try:
                    for child in self.not_found_tree.get_children():
                        self.not_found_tree.delete(child)
                except:
                    pass

                self.result_label.config(text=f"Encontrados: {len(self.comparison.result.df_found)} | Não Encontrados: {self.not_found_count}")

                self.not_found_count = 0
                for index, row in self.comparison.result.df_not_found_income.iterrows():
                    self.not_found_tree.insert('', ttk.END, values=(row['values'], row['names'], row['origin']), tags=('entradas',))
                    self.not_found_count += 1

                for index, row in self.comparison.result.df_not_found_comp.iterrows():
                    self.not_found_tree.insert('', ttk.END, values=(row['values'], row['names'], row['origin']), tags=('comprobantes',))
                    self.not_found_count += 1

                self.result_label.config(text=f"Encontrados: {len(self.comparison.result.df_found)} | Não Encontrados: {self.not_found_count}")

        run_in_bg()

    def convert_statement_to_table(self, desired_pattern: DesiredPattern = DesiredPattern.incoming):

        income_text = self.income_entry.get("1.0", "end-1c").split('\n')

        values_pattern = r'R\$ ([^\t]+)'
        outgoing_value_pattern = r'- R\$ ([^\t]+)'
        values = []
        names = []
        ids = []

        for item in income_text:
            value = False

            if desired_pattern != DesiredPattern.outgoing:
                value_match = re.search(values_pattern, item)
                negative_value_match = re.search(outgoing_value_pattern, item)
                names_match = re.search(r'\t([^\t]+)', item)
                criteria = value_match and not negative_value_match
                self.conversion_type = "Entradas"
            else:
                outgoing_value_pattern = r'-R\$ ([^\t]+)'
                negative_value_match = re.search(outgoing_value_pattern, item)
                value_match = re.search(values_pattern, item)
                names_match = re.search(r'\tTAR enviado:([^\t]+)', item)

                criteria = value_match and negative_value_match
                self.conversion_type = "Saídas"

            if criteria:
                value_str = value_match.group(1)
                value_str = value_str.replace('.', '')
                value = value_str.replace(',', '.')

            else:
                row = item.split('\t')
                for each in row:
                    try:
                        each = each.replace('.', '')
                        each = each.replace(',', '.')

                        value = float(each)
                        break
                    except:
                        pass
            if value:
                values.append(float(value))
            else:
                values.append(None)

            # Extract names

            if names_match:
                name = names_match.group(1)
                names.append(name)
            else:
                names.append(None)

            ids.append(uuid.uuid4().hex)

        df = pd.DataFrame({'values': values, 'names': names})
        df.dropna(subset=['values', 'names'], how='all', inplace=True)

        result = ""
        total_incoming = 0

        # process only positive values:
        for index, row in df[~pd.isna(df['values'])].iterrows():
            result += f"""{str(row['values']).replace('.', ',')}"""
            result += f"""\t{str(row['names'])}"""
            total_incoming += float(row['values'])
            result += "\n"

        self.sum_label.config(

            text=f"Total em {self.conversion_type}: {float(total_incoming):.2f}")

        pyperclip.copy(str(result))


MainWindow()
