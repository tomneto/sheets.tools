import collections
import json
import multiprocessing
import os
import sys
import threading

from typing import Union, Type
import ttkbootstrap as ttk
from icecream import ic
from cryptography.fernet import Fernet

from system import hide_file_windows


class Configuration:
    label: str = ""
    default = None
    value = None
    value_type = None
    hidden: bool = False
    entry_name: str

    def __init__(self, type: type, label: Union[str, None] = None, default=None, hidden: bool = False):

        self.default = default
        self.value_type = type
        self.hidden = hidden

        if label is not None:
            self.label = label
            self.entry_name = f"""{label.lower().replace(" ", "_")}"""

    def as_dict(self):
        return {"label": self.label, "default": self.default, "value": self.get(), "type": str(self.value_type)}

    def set(self, obj: ttk.Entry):
        try:

            value = obj.get()
            if value is not None:
                self.value = value
                self.get()

        except Exception as e:
            error_window = ttk.Toplevel("Config Error")
            error_window.geometry("500x500")
            error_window.rowconfigure(0, weight=1)  # Make the window vertically resizable
            error_window.columnconfigure(0, weight=1)
            error_label = ttk.Label(error_window, text=str(e))
            error_label.grid()

    def get(self):
        if not isinstance(self.value, self.value_type):

            if self.value_type == list and len(self.value):
                self.value = self.value.split(",")

            if self.value is not None:
                self.value = self.value_type(self.value)
        return self.value


class Config:

    language = Configuration(label="Language", type=str, default="pt-br")

    key = Configuration(type=str, hidden=True)
    comparison_threshold = Configuration(label="Comparison Threshold", default=80, type=int)
    tcb_user = Configuration(label="TCB User", type=str)
    tcb_password = Configuration(label="TCB Password", type=str)
    ignored_income_names = Configuration(label="Nomes Para Ignorar (Entradas)", type=list, default=[])

    _ignored: list = ["iter", "save", "load", "_ignored", "_conf_fp", "type_mapping", "saving"]
    _conf_fp: str = "./conf.json"
    saving: bool = False

    # Mapping string types to Python types
    type_mapping = {
        'int': int,
        'str': str,
        'float': float,
        'bool': bool,
        'NoneType': type(None),
        'list': list,
        'dict': dict
    }

    def _configurations(self) -> list:
        return [conf for conf in self.__dir__() if not conf.startswith("_") and conf not in self._ignored and not self.__getattribute__(conf).hidden]

    def __init__(self):

        for conf in self._configurations():
            this_conf: Configuration = self.__getattribute__(conf)
            if this_conf.default is not None and this_conf.value is None:
                this_conf.value = this_conf.value_type(this_conf.default)


        # Attempt to load existing configuration
        self.load()

    def iter(self):
        for conf in self._configurations():
            this_conf: Configuration = self.__getattribute__(conf)
            yield this_conf

    def _save(self, content):
        print("Saving Config")
        # Remove old configuration file if exists
        try:
            os.remove(self._conf_fp)
        except:
            pass

        # Save the configuration to JSON
        with open(self._conf_fp, "+a") as conf_file:
            ic(content)
            conf_file.write(json.dumps(content))

        if sys.platform == "win32":
            hide_file_windows(self._conf_fp)

    def save(self, content):

        if not self.saving:
            self.saving = True
            save_process = multiprocessing.Process(target=self._save, args=(content,))
            save_process.run()
            self.saving = False

        return self.iter()

    def load(self):
        # Load configuration from JSON and apply types
        if not os.path.exists(self._conf_fp):
            return  # If no config file exists, skip loading

        with open(self._conf_fp, "r") as conf_file:
            try:
                content = json.loads(conf_file.read())
            except:
                content = {}

            for conf_data in content:
                for conf in self._configurations():
                    this_conf: Configuration = self.__getattribute__(conf)
                    if this_conf.label == conf_data['label']:
                        # Apply the correct type and value
                        this_conf.value_type = self.type_mapping.get(conf_data['type'], str)
                        if conf_data['value'] is not None:
                            this_conf.value = conf_data["value"]
                            this_conf.get()
