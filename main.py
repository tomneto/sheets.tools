import os
import re
import threading
import uuid
from tkinter import PhotoImage

import pandas as pd
import ttkbootstrap as ttk
from fuzzywuzzy import fuzz
import pyperclip

comparison_threshold = 80


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


def get_values_and_names(content):
    values_pattern = r'R\$ ([^\t]+)'

    values = []
    names = []
    ids = []

    for item in content:
        print(item)
        print(item.split('\t'))
        value_match = re.search(values_pattern, item)
        value = False
        if value_match:
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
        names_match = re.search(r'\t([^\t]+)$', item)
        if names_match:
            name = names_match.group(1)
            names.append(name)
        else:
            names.append(None)
        ids.append(uuid.uuid4().hex)

    df = pd.DataFrame({"ids": ids, 'values': values, 'names': names, 'original': content})
    df.dropna(subset=['values', 'names'], how='all', inplace=True)
    return df


def clean_name(name):
    if isinstance(name, str):
        name = name.lower()

        to_ignore = ['pix', 'recebido', '-']
        for ignored_word in to_ignore:
            name = name.replace(ignored_word, '')

        # remove numbers from name
        name = re.sub(r'[0-9]+', '', name)

    return name


def fuzzy_similarity(name1: str, name2: str):
    if name1 != "" and name2 != "":
        name1 = clean_name(name1)
        name2 = clean_name(name2)

        for word_1 in name1.split(' '):
            for word_2 in name2.split(' '):
                if word_2 != "" and word_1 != "":
                    #print(f"Comparing {word_1, word_2}")
                    similarity = fuzz.token_sort_ratio(word_1, word_2)
                    if similarity >= comparison_threshold:
                        return True
                    #print(f"Comparing results false for {word_1, word_2}")

    return False


def relative_path(relative_path):
    absolute_path = os.path.dirname(__file__)
    full_path = os.path.join(absolute_path, relative_path)

    return full_path

class MainWindow:
    similar_rows = []
    not_found = []
    found_df = pd.DataFrame
    not_found_df = pd.DataFrame
    not_found_count = 0
    threads = {'submit': []}

    class Colors:

        comprobante_not_found = "#a83232"
        entrada_not_found = "#8c7f00"

    def __init__(self):

        self.root = ttk.Window(themename="darkly", iconphoto=relative_path('icon.png'))
        img = PhotoImage(file=relative_path('icon.png'))
        self.root.iconbitmap(relative_path('icon.ico'))
        self.root.iconphoto(False, img)
        self.root.title("Diferença em Comprovantes e Entradas")

        # Comprobantes Entry
        comprobantes_label = ttk.Label(self.root, text="Comprovantes:")
        comprobantes_label.grid(row=0, column=0, sticky="w")

        self.comprobantes_entry = ttk.Text(self.root, height=5, width=40)
        self.comprobantes_entry.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Entradas Entry
        entradas_label = ttk.Label(self.root, text="Entradas:")
        entradas_label.grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.entradas_entry = ttk.Text(self.root, height=5, width=40)
        self.entradas_entry.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

        # Submit Button
        submit_button = ttk.Button(self.root, text="Comparar", command=self.submit_with_delay)
        submit_button.grid(row=4, column=0, pady=(10, 0))

        # Submit Button
        copy_result = ttk.Button(self.root, text="Copiar Resultado", command=self.copy_result)
        copy_result.grid(row=5, column=0, pady=(10, 0))

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
        self.not_found_tree.tag_configure('comprobantes', background=self.Colors.comprobante_not_found)
        self.not_found_tree.tag_configure('entradas', background=self.Colors.entrada_not_found)
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

    def process_comprobante(self, comprobante_row, df_entradas, similar_rows, not_found):
        found_similarity = False
        already_used = False

        for _, entrada_row in df_entradas.iterrows():
            # Compare values for equality
            if comprobante_row['values'] == entrada_row['values']:
                # Calculate similarity for names
                if comprobante_row['names'] is not None and entrada_row['names'] is not None:
                    name_similarity = fuzzy_similarity(comprobante_row['names'], entrada_row['names'])
                    # Check if names are similar
                    if name_similarity:
                        found_similarity = True
                        already_used = entrada_row['ids'] in [e['ids'] for e in similar_rows]
                        if not already_used:
                            similar_rows.append({
                                'ids': entrada_row['ids'],
                                'values': entrada_row['values'],
                                'names': entrada_row['names'],
                                "origin": "entradas",
                                "original": entrada_row['original'],
                                "matching_id": comprobante_row['ids']
                            })
                            break

        if found_similarity and not already_used:
            similar_rows.append({
                'ids': comprobante_row['ids'],
                'values': comprobante_row['values'],
                'names': comprobante_row['names'],
                "origin": "comprobantes",
                "original": comprobante_row['original']
            })
        else:
            not_found.append({
                'ids': comprobante_row['ids'],
                'values': comprobante_row['values'],
                'names': comprobante_row['names'],
                "origin": "comprobantes",
                "original": comprobante_row['original']
            })

    def on_submit(self, comprobantes_text, entradas_text):

        self.similar_rows = []
        self.not_found = []

        # Create DataFrames for both comprobantes and entradas
        self.df_comprobantes = get_values_and_names(comprobantes_text)
        self.df_entradas = get_values_and_names(entradas_text)

        self.sum_comprobantes = self.df_comprobantes['values'].sum()
        self.sum_entradas = self.df_entradas['values'].sum()

        for _, comprobante_row in self.df_comprobantes.iterrows():
            found_similarity = False
            already_used = False
            for _, entrada_row in self.df_entradas.iterrows():
                # Compare values for equality
                if comprobante_row['values'] == entrada_row['values']:
                    # Calculate similarity for names
                    if comprobante_row['names'] is not None and entrada_row['names'] is not None:
                        name_similarity = fuzzy_similarity(comprobante_row['names'], entrada_row['names'])
                        # Check if names are similar
                        if name_similarity:
                            found_similarity = True
                            already_used = entrada_row['ids'] in [e['ids'] for e in self.similar_rows]
                            if not already_used:
                                #print(f"\n\nAppending to similar: {entrada_row['names']} matching with: {comprobante_row['names']} \n\n")
                                self.similar_rows.append(
                                    {'ids': entrada_row['ids'], 'values': entrada_row['values'],
                                     'names': entrada_row['names'], "origin": "entradas",
                                     "original": entrada_row['original'], "matching_id": comprobante_row['ids']})
                                break

            #print(f"Comprobante Match trying to append...")
            if found_similarity and not already_used:
                #print(f"Comprobante Match: {comprobante_row['names'], comprobante_row['values']}")
                self.similar_rows.append({'ids': comprobante_row['ids'], 'values': comprobante_row['values'],
                                 'names': comprobante_row['names'], "origin": "comprobantes", "original": comprobante_row['original']})

            else:
                #print(f"Comprobante don't Match: {comprobante_row['names'], comprobante_row['values']}")
                self.not_found.append(
                    {'ids': comprobante_row['ids'], 'values': comprobante_row['values'],
                 'names': comprobante_row['names'], "origin": "comprobantes", "original": comprobante_row['original']})  # Add to not found entradas

        for _, entrada_row in self.df_entradas.iterrows():
            found_similarity = False
            already_used = False
            for _, comprobante_row in self.df_comprobantes.iterrows():
                # Compare values for equality
                if comprobante_row['names'] is not None:
                    if comprobante_row['values'] == entrada_row['values']:
                        # Calculate spaCy similarity for names
                        if comprobante_row['names'] is not None and entrada_row['names'] is not None:
                            name_similarity = fuzzy_similarity(comprobante_row['names'], entrada_row['names'])
                            # Check if names are similar
                            if name_similarity:
                                found_similarity = True
                                already_used = entrada_row['ids'] in [e['ids'] for e in self.similar_rows]
                                break

            if found_similarity and not already_used:
                #print(f"Entrada Match: {entrada_row['names'], entrada_row['values']}")
                self.similar_rows.append({'ids': entrada_row['ids'], 'values': entrada_row['values'], 'names': entrada_row['names'], "origin": "entradas", "original": entrada_row['original']})
            else:
                #print(f"Entrada don't Match: {entrada_row['names'], entrada_row['values']}")
                self.not_found.append({'ids': entrada_row['ids'], 'values': entrada_row['values'], 'names': entrada_row['names'], "origin": "entradas", "original": entrada_row['original']})

        # Create DataFrames from the result rows
        self.found_df = pd.DataFrame(self.similar_rows)
        self.not_found_df_entradas = pd.DataFrame(self.not_found)  # Create DataFrame for not found entradas

        try:
            self.not_found_df_entradas = self.not_found_df_entradas[~self.not_found_df_entradas['ids'].isin([e["ids"] for e in self.similar_rows if len(self.similar_rows)])]
            self.not_found_df_entradas = self.not_found_df_entradas.sort_values(by='values', ascending=False)
        except:
            pass


    def submit_with_delay(self,):

        comprobantes_text = self.comprobantes_entry.get("1.0", "end-1c").split('\n')
        entradas_text = self.entradas_entry.get("1.0", "end-1c").split('\n')

        self.threads['submit'].append(threading.Thread(target=self.on_submit, args=(comprobantes_text, entradas_text)))

        def run_in_bg():
            for idx, thr in enumerate(self.threads['submit']):
                del self.threads['submit'][idx]
                thr.start()
                thr.join()

                self.sum_label.config(
                    text=f"Total em Comprovantes: {float(self.sum_comprobantes):.2f} | Total em Entradas: {float(self.sum_entradas):.2f}\nTotal de diferença: {float(self.sum_comprobantes - self.sum_entradas):.2f}")

                # Update the Treeview with the similar result
                for child in self.found_tree.get_children():
                    self.found_tree.delete(child)

                try:
                    self.found_df = self.found_df.sort_values(by='values', ascending=False)
                    for index, row in self.found_df.iterrows():
                        self.found_tree.insert('', ttk.END, values=(row['values'], row['names']))
                except:
                    pass

                try:
                    for child in self.not_found_tree.get_children():
                        self.not_found_tree.delete(child)
                except:
                    pass

                self.result_label.config(
                    text=f"Encontrados: {len(self.found_df)} | Não Encontrados: {self.not_found_count}")

                self.not_found_count = 0
                for index, row in self.not_found_df_entradas.iterrows():

                    if row['origin'] == "comprobantes":
                        self.not_found_tree.insert('', ttk.END, values=(row['values'], row['names']),
                                                   tags=('comprobantes',))
                    elif row['origin'] == "entradas":
                        self.not_found_tree.insert('', ttk.END, values=(row['values'], row['names']),
                                                   tags=('entradas',))
                        self.not_found_count += 1

        run_in_bg()


    def copy_result(self):
        #print(self.found_df.head())
        result = ""

        result += "Encontrados\n"
        for index, row in self.found_df[self.found_df['origin'] == "comprobantes"].iterrows():
            # this must be green
            equivalent_entrada = list(self.found_df[self.found_df['matching_id'] == row['ids']].iterrows())[0][1]
            result += f"""{",".join([row['original'].replace("R$", "")])}\t\t{str(equivalent_entrada['original'])}\n"""

        not_found_entradas = self.not_found_df_entradas[self.not_found_df_entradas['origin'] == "entradas"].sort_values('values', ascending=False)
        not_found_comprovantes = self.not_found_df_entradas[self.not_found_df_entradas['origin'] == "comprobantes"].sort_values('values', ascending=False)

        # Assuming 'values' is the column you want to use for left join
        merged_df = pd.merge(not_found_entradas, not_found_comprovantes, on='values', how='left',
                             suffixes=('_entradas', '_comprovantes'))

        # Replace NaN values with '\t'
        merged_df.fillna('\t', inplace=True)

        result += "\n\nNão Encontrados\n"
        for index, row in merged_df.iterrows():
            result += f"""\t{",".join([row['original_entradas'].replace("R$", "")])}"""
            result += f"""\t\t{str(row['original_comprovantes'])}"""
            result += "\n"

        # result += "Entradas Faltantes\n\n"
        # for index, row in self.not_found_df_entradas[self.not_found_df_entradas['origin'] == "entradas"].iterrows():
        #     # this must be yellow
        #     result += f"""\t{",".join([row['original'].replace("R$", "")])}\n"""
#
        # result += "Comprovantes Faltantes\n\n"
        # for index, row in self.not_found_df_entradas[self.not_found_df_entradas['origin'] == "comprobantes"].iterrows():
        #     # this must be red
        #     result += f"""{",".join([row['original'].replace("R$", "")])}\n"""
#
        pyperclip.copy(result)
        return result


MainWindow()
