import re

import pandas as pd
import pyperclip
from typing import Type
from bs4 import BeautifulSoup
from icecream import ic
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


class TCBScraper:


    def __init__(self):

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


class TCBBrowser:

    url: str = "https://app.tcbdigital.com.br/#/auth/login"
    browser: webdriver.Chrome
    user: str = ""
    password: str = ""

    class Selector:

        selection_type: By.CSS_SELECTOR = By.CSS_SELECTOR
        email: str = """input[formcontrolname="Email"]"""
        password: str = """input[formcontrolname="Password"]"""
        login_btn: str = """"kt_login_signin_submit"""

    def __call__(self, user: str, password: str):
        self.browser = webdriver.Chrome()
        self.browser.get(self.url)
        self.browser.maximize_window()

        self.user = user
        self.password = password

        email_element = None
        try:
            # Wait for up to 10 seconds until the element is located
            email_element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((self.Selector.selection_type, self.Selector.email)))
        except Exception as e:
            email_element = None

        ic(email_element)

        if email_element is not None:
            email_in = self.browser.find_element(self.Selector.selection_type, self.Selector.email)
            email_in.send_keys(self.user)

            password_in = self.browser.find_element(self.Selector.selection_type, self.Selector.password)
            password_in.send_keys(self.password)
            password_in.send_keys(Keys.RETURN)

