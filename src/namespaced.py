import pathlib

from json import JSONEncoder


def _default(self, obj):
    return str(obj)


_default.default = JSONEncoder.default
JSONEncoder.default = _default


class Namespaced:
    def __add__(self, other):
        return str(self) + other

    def __init__(self, value, namespace='minecraft'):
        str_value = str(value)
        parts = str_value.split(':')
        self.namespace = parts[-2] if ':' in str_value else namespace
        self.value = pathlib.PurePosixPath(parts[-1])
        self.str = str(self.value)

    def __repr__(self):
        return self.namespace + ':' + str(self.value)

    def child(self, value):
        return Namespaced(self.value / value, self.namespace)

    def parent(self):
        return Namespaced('/'.join(str(self).split('/')[:-1]))
