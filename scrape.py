import re

import pandas as pd
import pyperclip
from icecream import ic
from bs4 import BeautifulSoup

# Open the local HTML file
with open('/Volumes/Git/Clientes/TCB/sheets.tools/html/pingduoduo.html', 'r') as file:
    html_content = file.read()

# Parse the HTML content
soup = BeautifulSoup(html_content, 'html.parser')

ng_star_inserted_elements = soup.body.find_all(class_='ng-star-inserted')

values = []
names = []

for tr_element in ng_star_inserted_elements:
    td_elements = tr_element.find_all('td')
    name = None

    for td in td_elements:

        spans = td.find_all('span')

        names_match = re.search(r'TAR enviado:([^\t]+)', td.get_text())
        if names_match is not None:
            name = names_match.group()

        for span in spans:
            negative_value_match = re.search(r'-R\$.*', span.get_text())

            if negative_value_match and name is not None:
                value_str = negative_value_match.group()
                value_str = value_str.replace('.', '')
                value = value_str.replace(',', '.')

                names.append(name)
                values.append(float(value.replace("-R$", "")))

df = pd.DataFrame({'values': values, 'names': names})
df.dropna(subset=['values', 'names'], how='all', inplace=True)
result = ""
total_ = 0


# process only positive values:
for index, row in df[~pd.isna(df['values'])].iterrows():
    result += f"""{str(row['values']).replace('.', ',')}"""
    result += f"""\t{str(row['names'])}"""
    total_ += float(row['values'])
    result += "\n"

pyperclip.copy(str(result))


