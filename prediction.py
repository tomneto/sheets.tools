import re

import pandas as pd
from fuzzywuzzy import fuzz
from uuid import uuid4
import pyperclip

from icecream import ic
from typing import Union, Type

from config import comparison_threshold


def get_values_and_names(content: Union[list, str], skipcols=0) -> pd.DataFrame:
    values_pattern = r'R\$ ([^\t]+)'

    values = []
    names = []
    ids = []

    if isinstance(content, str):
        content = content.split('\n')

    for item in content:
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
        ids.append(uuid4().hex)

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
                    similarity = fuzz.token_sort_ratio(word_1, word_2)
                    if similarity >= comparison_threshold:
                        return True

    return False


class Result:
    df_found: pd.DataFrame
    df_not_found_income: pd.DataFrame
    df_not_found_comp: pd.DataFrame
    df_duplicated: pd.DataFrame

    similar_rows: list
    not_found: list

    def __init__(self, comparison):
        self.comparison = comparison

        self.similar_rows = self.comparison.similar_rows
        self.not_found = self.comparison.not_found

        self.df_found = pd.DataFrame(self.comparison.similar_rows)
        self.df_not_found_income = pd.DataFrame(self.comparison.not_found)
        self.df_duplicated = pd.DataFrame(self.comparison.duplicated)

        try:
            self.df_not_found_income = self.df_not_found_income[(~self.df_not_found_income['ids'].isin([e["ids"] for e in self.comparison.similar_rows if len(self.comparison.similar_rows)])) & (self.df_not_found_income["origin"] == "entradas")]
            self.df_not_found_income = self.df_not_found_income.sort_values(by='values', ascending=False)

        except:
            pass

        try:
            self.df_not_found_comp = self.comparison.df_comp[~self.comparison.df_comp["ids"].isin(self.comparison.already_used_comp_ids)]
            self.df_not_found_comp['origin'] = "comprobantes"
        except:
            pass


class Comparison:
    
    df_income: pd.DataFrame
    df_comp: pd.DataFrame

    already_used_comp_ids: list = []
    already_used_income_ids: list = []
    
    similar_rows: list = []
    not_found: list = []
    duplicated: list = []

    result: Result

    def __init__(self, df_income: pd.DataFrame, df_comp: pd.DataFrame):
        self.df_income = df_income
        self.df_comp = df_comp

        self.process()

    def process(self) -> Result:
        
        for _, comp_row in self.df_comp[~self.df_comp["ids"].isin(self.already_used_comp_ids)].iterrows():

            if comp_row['names'] is not None:

                found_similarity = False
                income_already_used = False
                comp_already_used = False

                for _, income_row in self.df_income[~self.df_income["ids"].isin(self.already_used_income_ids)].iterrows():

                    if comp_row['values'] == income_row['values']:

                        if income_row['names'] is not None:
                            name_similarity = fuzzy_similarity(comp_row['names'], income_row['names'])

                            if name_similarity:
                                found_similarity = True

                                comp_already_used = comp_row['ids'] in [e['ids'] for e in self.similar_rows]
                                income_already_used = income_row['ids'] in [e['ids'] for e in self.similar_rows]

                                if not income_already_used and not comp_already_used:
                                    self.similar_rows.append(
                                        {'ids': income_row['ids'], 'values': income_row['values'],
                                         'names': income_row['names'], "origin": "entradas",
                                         "original": income_row['original'], "matching_id": comp_row['ids']})
                                    self.already_used_comp_ids.append(comp_row['ids'])
                                    self.already_used_income_ids.append(income_row['ids'])
                                    break

                if found_similarity and not comp_already_used and not income_already_used:
                    self.similar_rows.append({'ids': comp_row['ids'], 'values': comp_row['values'],
                                              'names': comp_row['names'], "origin": "comprobantes",
                                              "original": comp_row['original']})
                else:
                    self.not_found.append(
                        {'ids': comp_row['ids'], 'values': comp_row['values'],
                         'names': comp_row['names'], "origin": "comprobantes",
                         "original": comp_row['original']})

                self.already_used_comp_ids.append(comp_row['ids'])

        for _, income_row in self.df_income[~self.df_income["ids"].isin(self.already_used_income_ids)].iterrows():

            if income_row['names'] is not None:

                found_similarity = False
                income_already_used = False
                comp_already_used = False

                for _, comp_row in self.df_comp[~self.df_comp["ids"].isin(self.already_used_comp_ids)].iterrows():
                    if comp_row['names'] is not None:
                        if comp_row['values'] == income_row['values']:
                            # Calculate spaCy similarity for names
                            if income_row['names'] is not None:
                                name_similarity = fuzzy_similarity(comp_row['names'], income_row['names'])
                                # Check if names are similar
                                if name_similarity:
                                    found_similarity = True
                                    comp_already_used = comp_row['ids'] in [e['ids'] for e in self.similar_rows]
                                    income_already_used = income_row['ids'] in [e['ids'] for e in self.similar_rows]
                                    break

                if found_similarity and not income_already_used and not comp_already_used:
                    self.similar_rows.append(
                        {'ids': income_row['ids'], 'values': income_row['values'], 'names': income_row['names'],
                         "origin": "entradas", "original": income_row['original']})

                else:
                    self.not_found.append(
                        {'ids': income_row['ids'], 'values': income_row['values'], 'names': income_row['names'],
                         "origin": "entradas", "original": income_row['original']})

                self.already_used_income_ids.append(income_row["ids"])

        self.result = Result(self)
        ic(self.result.__dict__)
        return self.result

    def copy_result(self):
        result = ""
        already_used = []

        if len(self.result.df_found):
            result += "Encontrados\n"
            for index, row in self.result.df_found[self.result.df_found['origin'] == "comprobantes"].iterrows():
                equivalent_incoming = list(self.result.df_found[self.result.df_found['matching_id'] == row['ids']].iterrows())[0][1]
                result += f"""{",".join([row['original'].replace("R$", "")])}\t\t{str(equivalent_incoming['original'])}\n"""

        not_found_income = self.result.df_not_found_income.sort_values('values', ascending=False)
        not_found_comp = self.result.df_not_found_comp.sort_values('values', ascending=False)

        merged_df = pd.merge(not_found_income, not_found_comp, on='values', how='left', suffixes=('_entradas', '_comprabantes'))
        merged_df.fillna('\t', inplace=True)

        result += "\n\nEntradas Não Encontradas (Verdes)\n"
        for index, row in merged_df.iterrows():
            ic(row)
            if row['origin_entradas'] != "\t":
                result += f"""\t{",".join([row['original_entradas'].replace("R$", "")])}"""
                result += f"""\t\t{str(row['original_comprabantes'])}"""
                result += "\n"

        result += "\n\nComprovantes com Entradas Semelhantes (Amarelos)\n"
        for index, row in merged_df.iterrows():
            if row['origin_comprabantes'] != "\t":
                # result += f"""\t{",".join([row['original_entradas'].replace("R$", "")])}"""
                result += f"""\t{str(row['original_comprabantes'])}"""
                result += "\n"
                already_used.append(str(f"{index} {row['original_comprabantes']}"))

        result += "\n\nComprovantes Não Encontrados (Vermelhos)\n"
        for index, row in enumerate(self.not_found):
            if row["origin"] == "comprobantes" and row['original'] != "\t" and str(
                    f"{index} {str(row['original'])}") not in already_used:
                # result += f"""\t{",".join([row['original_entradas'].replace("R$", "")])}"""
                result += f"""\t{str(row['original'])}"""
                result += "\n"

        pyperclip.copy(result.encode('utf-8').decode('utf-8'))

        return result
