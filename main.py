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

import scrape
from config import Config
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


def generate_treeview(window: ttk.Window):
        # Similar Result Treeview
        tree = ttk.Treeview(window, columns=('values', 'names', "origin"), show='headings')
        tree.bind("<Control-c>", lambda x: copy_from_treeview(tree, x))
        tree.bind("<Command-c>", lambda x: copy_from_treeview(tree, x))
        tree.heading('values', text='Valor')
        tree.heading('names', text='Nome')
        tree.heading('origin', text='Fonte')

        # Not Found Treeview
        return tree


class MainWindow:
    config: Config = Config()

    df_comp: pd.DataFrame
    df_income: pd.DataFrame
    
    df_found: pd.DataFrame

    df_not_found_comp: pd.DataFrame
    df_not_found_income: pd.DataFrame

    not_found_count: int = 0

    threads: dict = {'submit': []}
    conversion_type: str = "Entradas"

    comparison: Comparison = Comparison()

    sum_comp: int = 0
    sum_income: int = 0

    browser: scrape.TCBBrowser = scrape.TCBBrowser()

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

        self.tree_found_comp_label = ttk.Label(self.root, text="Comprovantes Encontrados (OK):")
        self.tree_found_comp_label.grid(row=0, column=1)

        self.tree_found_comp = generate_treeview(self.root)
        self.tree_found_comp.grid(row=1, column=1, rowspan=3, padx=5, pady=5, sticky="nsew")

        self.not_found_comp_label = ttk.Label(self.root, text="Comprovantes Não Encontrados (VERIFICAR):")
        self.not_found_comp_label.grid(row=4, column=1)

        self.tree_not_found_comp = generate_treeview(self.root)
        self.tree_not_found_comp.grid(row=5, column=1, rowspan=3, padx=5, sticky="nsew")

        self.tree_found_income_label = ttk.Label(self.root, text="Entradas Encontradas (OK):")
        self.tree_found_income_label.grid(row=0, column=2)

        self.tree_found_income = generate_treeview(self.root)
        self.tree_found_income.grid(row=1, column=2, rowspan=3, padx=5, pady=5, sticky="nsew")

        self.not_found_income_label = ttk.Label(self.root, text="Entradas Não Encontradas (INCLUIR):")
        self.not_found_income_label.grid(row=4, column=2)

        self.tree_not_found_income = generate_treeview(self.root)
        self.tree_not_found_income.grid(row=5, column=2, rowspan=3, padx=5, sticky="nsew")

        self.trees = [self.tree_found_comp, self.tree_not_found_comp, self.tree_found_income, self.tree_not_found_income]

        # Submit Button
        submit_button = ttk.Button(self.root, text="Comparar", command=self.compare_income_comp)
        submit_button.grid(row=4, column=0, pady=(10, 0))

        convert_button_income = ttk.Button(self.root, text="Converter Entradas", command=self.convert_statement_to_table)
        convert_button_income.grid(row=5, column=0, pady=(10, 0))
        
        convert_button_outgoing = ttk.Button(self.root, text="Converter Saidas", command=lambda: self.convert_statement_to_table(DesiredPattern.outgoing))
        convert_button_outgoing.grid(row=6, column=0, pady=(10, 0))

        self.copy_result = ttk.Button(self.root, text="Copiar Resultado", command=self.comparison.copy_result)
        self.copy_result.grid(row=7, column=0, pady=(10, 0))

        self.open_browser = ttk.Button(self.root, text="Abrir Site", command=self.open_tcb_website)
        self.open_browser.grid(row=9, column=0, pady=(10, 10))

        self.menu = ttk.Menu(self.root)
        self.menu.add_command(label="Config", command=self.open_config)

        self.open_config = ttk.Button(self.root, text="Configuracoes", command=self.open_config)
        self.open_config.grid(row=8, column=0, pady=(10, 0))

        # Result Label for Length
        self.result_label = ttk.Label(self.root, text="")
        self.result_label.grid(row=8, column=0, columnspan=3, pady=(10, 0))

        # Label for Sum of values
        self.sum_label = ttk.Label(self.root, text="")
        self.sum_label.grid(row=9, column=0, columnspan=3, pady=(5, 10))

        # Configure resizing behavior
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(3, weight=1)

        self.root.mainloop()

    def open_tcb_website(self):
        self.config.load()
        self.browser(self.config.tcb_user.value, self.config.tcb_password.value)

    def open_config(self):
        self.config_window = ttk.Toplevel(title="Configurações")
        self.config_window.geometry("500x500")  # Set initial size (optional)
        self.config_window.rowconfigure(0, weight=1)  # Make the window vertically resizable
        self.config_window.columnconfigure(0, weight=1)  # Make the window horizontally resizable

        last_row_idx = 0

        for idx, conf in enumerate(self.config.iter()):
            label_name = f"{idx}_label"
            self.__setattr__(label_name, ttk.Label(self.config_window, text=f"{conf.label}: "))
            this_label: ttk.Label = self.__getattribute__(label_name)
            this_label.grid(row=idx, column=0, columnspan=1, pady=(10, 0), sticky="e")  # Align label to the west (left)

            self.__setattr__(conf.entry_name, ttk.Entry(self.config_window, width=10))
            this_entry: ttk.Entry = self.__getattribute__(conf.entry_name)
            this_entry.grid(row=idx, column=1, columnspan=3, pady=(10, 0),
                            sticky="ew")  # Make the entry expand horizontally
            if conf.value is not None:
                this_entry.insert(0, conf.value)

            last_row_idx = idx

        self.config_save_button = ttk.Button(self.config_window, text="Salvar", command=self.save_config)
        self.config_save_button.grid(row=last_row_idx + 1, column=1, columnspan=2, pady=(10, 10), sticky="ew")

        # Configure the columns and rows for responsiveness
        for col in range(5):  # Assume up to 5 columns
            self.config_window.grid_columnconfigure(col, weight=1)  # Make each column expandable
        for row in range(last_row_idx + 2):  # Configure rows up to the last row
            self.config_window.grid_rowconfigure(row, weight=1)

    def save_config(self):
        content = []
        for conf in self.config.iter():

            conf.set(self.__getattribute__(conf.entry_name))
            conf_dict = conf.as_dict()
            conf_dict['type'] = conf.value_type.__name__  # Store the type as a string
            content.append(conf_dict)

        self.config.save(content)

    def on_submit(self, comp_text: list, income_text: list):

        to_ignore = self.config.ignored_income_names.get()
        self.df_comp = get_values_and_names(comp_text, ignored=to_ignore)
        self.df_income = get_values_and_names(income_text, ignored=to_ignore)

        self.sum_comp = self.df_comp['values'].sum()
        self.sum_income = self.df_income['values'].sum()

        self.comparison = self.comparison(df_income=self.df_income, df_comp=self.df_comp)

    def clean_trees(self):
        for tree in self.trees:
            # Update the Treeview with the similar result
            for child in tree.get_children():
                tree.delete(child)


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

                self.clean_trees()

                try:
                    for index, row in self.comparison.result.df_found.iterrows():
                        if row['origin'] == "comp":
                            self.tree_found_comp.insert('', ttk.END, values=(row['values'], row['names'], "Comprovante"))
                except:
                    pass

                for index, row in self.comparison.result.df_not_found_income.iterrows():
                    self.tree_not_found_income.insert('', ttk.END, values=(row['values'], row['names'], 'Entrada'), tags=('entradas',))

                for index, row in self.comparison.result.df_not_found_comp.iterrows():
                    self.tree_not_found_comp.insert('', ttk.END, values=(row['values'], row['names'], 'Comprovante'), tags=('comprobantes',))

                self.result_label.config(text=f"""Comprovantes Encontrados: {len(self.comparison.result.df_found[self.comparison.result.df_found["ids"].isin(self.comparison.already_used_comp_ids)])} | Comprovantes Não Encontrados: {len(self.comparison.result.df_not_found_comp)}\nEntradas Encontradas: {len(self.comparison.result.df_found[self.comparison.result.df_found["ids"].isin(self.comparison.already_used_income_ids)])} | Entradas Não Encontradas: {len(self.comparison.result.df_not_found_income)}""")

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
