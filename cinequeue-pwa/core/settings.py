"""App settings persistence — JSON file backed."""

import json
import os


class Settings:
    _data = {}
    _path = None

    @classmethod
    def init(cls, config_dir=None):
        if config_dir is None:
            config_dir = os.path.expanduser('~')
        cls._path = os.path.join(config_dir, 'cinequeue.json')

    @classmethod
    def _file(cls):
        if cls._path is None:
            cls.init()
        return cls._path

    @classmethod
    def load(cls):
        try:
            f = cls._file()
            if os.path.exists(f):
                with open(f) as fp:
                    cls._data = json.load(fp)
        except Exception:
            pass
        return cls._data

    @classmethod
    def save(cls, updates):
        cls._data.update(updates)
        try:
            with open(cls._file(), 'w') as fp:
                json.dump(cls._data, fp, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def get(cls, key, default=''):
        val = cls._data.get(key)
        if val is None:
            return default
        return val
