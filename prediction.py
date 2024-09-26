import re

import pandas as pd
from fuzzywuzzy import fuzz
from uuid import uuid4
import pyperclip

from icecream import ic
from typing import Union, Type
from config import Config


config = Config()


def get_values_and_names(content: Union[list, str], skipcols=0, ignored: Union[list, None] = None) -> pd.DataFrame:
    values_pattern = r'R\$ ([^\t]+)'

    values = []
    names = []
    ids = []

    if isinstance(content, str):
        content = content.split('\n')

    filtered_content = []

    for idx, item in enumerate(content):
        ignore: bool = False

        if ignored is not None:
            for name_to_ignore in ignored:
                if re.search(fr"{name_to_ignore}", item, re.IGNORECASE):
                    ignore = True
                    break

        if not ignore:
            value_match = re.search(values_pattern, item)
            value = None

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

            values.append(float(value) if value else None)

            names_match = re.search(r'\t([^\t]+)$', item)
            if names_match:
                name = names_match.group(1)
                names.append(name)
            else:
                names.append(None)

            ids.append(uuid4().hex)

            filtered_content.append(item)

    df = pd.DataFrame({"ids": ids, 'values': values, 'names': names, 'original': filtered_content})
    df.dropna(subset=['values', 'names'], how='all', inplace=True)

    return df


def clean_name(name):
    if isinstance(name, str):
        name = name.lower()

        to_ignore = ['pix', 'recebido', '-', "ted", "tev"]
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
                    if similarity >= config.comparison_threshold.value:
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
        self.df_not_found_comp = pd.DataFrame(self.comparison.not_found)
        self.df_duplicated = pd.DataFrame(self.comparison.duplicated)

        try:
            self.df_not_found_income = self.df_not_found_income[(~self.df_not_found_income['ids'].isin([e["ids"] for e in self.comparison.similar_rows if len(self.comparison.similar_rows)])) & (self.df_not_found_income["origin"] == "income")]
            self.df_not_found_income = self.df_not_found_income.sort_values(by='values', ascending=False)

        except:
            pass

        try:
            self.df_not_found_comp = self.df_not_found_comp[(self.df_not_found_comp["origin"] == "comp")]
            self.df_not_found_comp.loc[:, 'origin'] = "comp"
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

    def __call__(self, df_income: pd.DataFrame, df_comp: pd.DataFrame):
        self.df_income = df_income
        self.df_comp = df_comp

        self.process()

        return self

    def process(self) -> Result:

        self.already_used_comp_ids: list = []
        self.already_used_income_ids: list = []

        self.similar_rows: list = []
        self.not_found: list = []
        self.duplicated: list = []
        
        for _, comp_row in self.df_comp[~self.df_comp["ids"].isin(self.already_used_comp_ids)].iterrows():

            if comp_row['names'] is not None:

                force_search = False
                found_similarity = False
                income_already_used = False
                comp_already_used = False

                name_pattern = '|'.join(re.escape(word) for word in clean_name(comp_row["names"]).split())

                quick_res = self.df_income[
                    (~self.df_income["ids"].isin(self.already_used_income_ids)) &
                    (self.df_income['names'].str.contains(name_pattern, case=False, regex=True)) &
                    (self.df_income["values"] == comp_row["values"])
                ]

                for _, qr in quick_res.iterrows():
                    force_search = False

                    comp_already_used = comp_row['ids'] in [e['ids'] for e in self.similar_rows]
                    income_already_used = qr['ids'] in [e['ids'] for e in self.similar_rows]

                    if not income_already_used and not comp_already_used:

                        name_similarity = fuzzy_similarity(comp_row['names'], qr['names'])

                        if name_similarity:
                            found_similarity = True

                        self.similar_rows.append(
                            {'ids': qr['ids'], 'values': qr['values'],
                             'names': qr['names'], "origin": "income",
                             "original": qr['original'], "matching_id": comp_row['ids']})
                        self.already_used_income_ids.append(qr['ids'])
                        break

                    force_search = True

                if not len(quick_res) or force_search:
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
                                             'names': income_row['names'], "origin": "income",
                                             "original": income_row['original'], "matching_id": comp_row['ids']})
                                        self.already_used_comp_ids.append(comp_row['ids'])
                                        self.already_used_income_ids.append(income_row['ids'])
                                        break

                if found_similarity and not comp_already_used and not income_already_used:
                    self.similar_rows.append({'ids': comp_row['ids'], 'values': comp_row['values'],
                                              'names': comp_row['names'], "origin": "comp",
                                              "original": comp_row['original']})
                else:
                    self.not_found.append(
                        {'ids': comp_row['ids'], 'values': comp_row['values'],
                         'names': comp_row['names'], "origin": "comp",
                         "original": comp_row['original']})

                self.already_used_comp_ids.append(comp_row['ids'])

        for _, income_row in self.df_income[~self.df_income["ids"].isin(self.already_used_income_ids)].iterrows():

            if income_row['names'] is not None:

                force_search = False
                found_similarity = False
                income_already_used = False
                comp_already_used = False

                name_pattern = '|'.join(re.escape(word) for word in clean_name(income_row["names"]).split())

                quick_res = self.df_comp[
                    (~self.df_comp["ids"].isin(self.already_used_comp_ids)) &
                    (self.df_comp['names'].str.contains(name_pattern, case=False, regex=True)) &
                    (self.df_comp["values"] == income_row["values"])
                    ]

                for _, qr in quick_res.iterrows():
                    force_search = False

                    comp_already_used = qr['ids'] in [e['ids'] for e in self.similar_rows]
                    income_already_used = income_row['ids'] in [e['ids'] for e in self.similar_rows]

                    if not income_already_used and not comp_already_used:

                        name_similarity = fuzzy_similarity(income_row['names'], qr['names'])

                        if name_similarity:
                            found_similarity = True
                            comp_already_used = qr['ids'] in [e['ids'] for e in self.similar_rows]
                            income_already_used = income_row['ids'] in [e['ids'] for e in self.similar_rows]
                            break

                    force_search = True

                if not len(quick_res) or force_search:
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
                         "origin": "income", "original": income_row['original']})

                else:
                    self.not_found.append(
                        {'ids': income_row['ids'], 'values': income_row['values'], 'names': income_row['names'],
                         "origin": "income", "original": income_row['original']})

                self.already_used_income_ids.append(income_row["ids"])

        self.result = Result(self)
        return self.result

    def copy_result(self):
        result = ""
        already_used = []

        if len(self.result.df_found):
            result += "Encontrados\n"
            for index, row in self.result.df_found[self.result.df_found['origin'] == "comp"].iterrows():
                equivalent_incoming = list(self.result.df_found[self.result.df_found['matching_id'] == row['ids']].iterrows())[0][1]
                result += f"""{",".join([row['original'].replace("R$", "")])}\t\t{str(equivalent_incoming['original'])}\n"""

        not_found_income = self.result.df_not_found_income.sort_values('values', ascending=False)
        not_found_comp = self.result.df_not_found_comp.sort_values('values', ascending=False)

        merged_df = pd.merge(not_found_income, not_found_comp, on='values', how='left', suffixes=('_income', '_comp'))
        merged_df.fillna('\t', inplace=True)

        result += "\n\nEntradas Não Encontradas (Verdes)\n"
        for index, row in merged_df.iterrows():
            try:
                if row['origin_income'] != "\t":
                    result += f"""\t{",".join([row['original_income'].replace("R$", "")])}"""
                    result += f"""\t\t{str(row['original_comp'])}"""
                    result += "\n"
            except:
                if row['origin'] != "\t":
                    result += f"""\t{",".join([row['original_income'].replace("R$", "")])}"""
                    result += "\n"

        result += "\n\nComprovantes com Entradas Semelhantes (Amarelos)\n"
        for index, row in merged_df.iterrows():
            try:
                if row['origin_comp'] != "\t":
                    result += f"""\t{str(row['original_comp'])}"""
                    result += "\n"
                    already_used.append(str(f"{index} {row['original_comp']}"))
            except:
                pass

        result += "\n\nComprovantes Não Encontrados (Vermelhos)\n"
        for index, row in enumerate(self.not_found):
            if row["origin"] == "comp" and row['original'] != "\t" and str(
                    f"{index} {str(row['original'])}") not in already_used:
                # result += f"""\t{",".join([row['original_income'].replace("R$", "")])}"""
                result += f"""\t{str(row['original'])}"""
                result += "\n"

        pyperclip.copy(result.encode('utf-8').decode('utf-8'))

        return result
