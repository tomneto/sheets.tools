import collections
import json
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
        return {"label": self.label, "default": self.default, "value": self.value_type(self.value), "type": str(self.value_type)}

    def set(self, obj: ttk.Entry):
        self.value = self.value_type(obj.get())


class Config:

    key = Configuration(type=str, hidden=True)
    comparison_threshold = Configuration(label="Semelhança Minima da Comparção", default=80, type=int)
    tcb_user = Configuration(label="Usuario TCB", type=str)
    tcb_password = Configuration(label="Senha TCB", type=str)

    _ignored: list = ["iter", "save", "load", "_ignored", "_conf_fp", "type_mapping"]
    _conf_fp: str = "./conf.json"

    # Mapping string types to Python types
    type_mapping = {
        'int': int,
        'str': str,
        'float': float,
        'bool': bool,
        'NoneType': type(None)
    }

    def _configurations(self) -> list:
        return [conf for conf in self.__dir__() if not conf.startswith("_") and conf not in self._ignored and not self.__getattribute__(conf).hidden]

    def __init__(self):

        # If defaults are set, assign them with appropriate types
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

    def _save(self, window):
        print("Saving Config")
        # Remove old configuration file if exists
        try:
            os.remove(self._conf_fp)
        except:
            pass

        # Save the configuration to JSON
        with open(self._conf_fp, "+a") as conf_file:
            content = []
            for idx, conf in enumerate(self.iter()):
                ic(conf)
                conf_dict = conf.as_dict()
                conf.set(window.__getattribute__(conf.entry_name))
                conf_dict['type'] = conf.value_type.__name__  # Store the type as a string
                content.append(conf_dict)
            conf_file.write(json.dumps(content))

        if sys.platform == "win32":
            hide_file_windows(self._conf_fp)

    def save(self, window):
        #threading.Thread(target=self._save, args=(window,)).start()
        self.save(window)

    def load(self):
        # Load configuration from JSON and apply types
        if not os.path.exists(self._conf_fp):
            return  # If no config file exists, skip loading

        with open(self._conf_fp, "r") as conf_file:
            content = json.loads(conf_file.read())
            for conf_data in content:
                for conf in self._configurations():
                    this_conf: Configuration = self.__getattribute__(conf)
                    if this_conf.label == conf_data['label']:
                        # Apply the correct type and value
                        this_conf.value_type = self.type_mapping.get(conf_data['type'], str)
                        if conf_data['value'] is not None:
                            this_conf.value = this_conf.value_type(conf_data['value'])
                        ic(this_conf.__dict__)