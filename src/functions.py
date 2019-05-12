from mcpack import (Function, FunctionTag)
from mcpacker.items import resolve
from datetime import datetime
import json

colors = [
    'black',
    'dark_blue',
    'dark_green',
    'dark_aqua',
    'dark_red',
    'dark_purple',
    'gold',
    'gray',
    'dark_gray',
    'blue',
    'green',
    'aqua',
    'red',
    'light_purple',
    'yellow'
]

join = lambda lines: '\n'.join(lines)

class FunctionWrapper(object):
    def __init__(self, body = ''):
        self.function = Function(body)
    def add_text(self, text):
        self.function.body += text
    def add_lines(self, lines):
        self.add_text(join(lines) + ("\n" if len(lines) else ""))
    def add_indexed(self, size, text):
        self.add_lines([text.replace("{i}", f"{i}") for i in range(size)])
    def set(self, pack, path, callback = None):
        if not len(self.function.body): return
        pack[path] = self.function
        if callback: callback()

class Functions(dict):
    def __init__(self, relpaths):
        for relpath in relpaths:
            self.add(relpath)
    def add(self, relpath, body = ['']):
        self[relpath] = FunctionWrapper(join(body))
    def add_data(self, templates, data, indexed = False):
        def get_data_str(name, data0):
            str = templates[name][0:]
            for key, value in data0.items():
                str = str.replace(key, value)
            return str
        for name, list in data.items():
            for entry in list:
                data_str = get_data_str(name, entry['data'])
                if indexed:
                    self[name].add_indexed(entry['n'], data_str)
                else:
                    self[name].add_text(data_str)
    def load(self, pack):
        if not "function_code" in pack.data: return
        [self[path].add_lines(lines) for path,lines in pack.data["function_code"].items()]
    def set(self, pack):
        for path, func in self.items():
            func.set(pack, resolve(path, pack))

class SelfTaggedFunction(FunctionWrapper):
    def __init__(self, pack, relpath, body = '', namespace = 'minecraft'):
        self.pack = pack
        self.relpath = relpath
        self.namespace = namespace
        self.fullpath = resolve(relpath, pack)
        super().__init__(body)
    def add_to_tag(self, path):
        if not self.relpath in self.pack[self.namespace].function_tags:
            self.create_tag()
        self.pack[self.namespace].function_tags[self.relpath].values.append(path)
    def create_tag(self):
        self.pack[resolve(self.relpath, None, self.namespace)] = FunctionTag()
    def set(self):
        super().set(self.pack, self.fullpath, lambda: self.add_to_tag(self.fullpath))

class Load(SelfTaggedFunction):
    def __init__(self, pack, objectives = []):
        super().__init__(pack, 'load')
        self.add_lines([f"scoreboard objectives add {name}" for name in objectives])

class Tick(SelfTaggedFunction):
    operations = [
        "set @a[scores={{{0}=1..}}] {0} 0",
        "add @a {} 0",
        "enable @a {}"
    ]
    def __init__(self, pack, body = ''):
        super().__init__(pack, 'tick', body)
        if pack.data and "options" in pack.data:
            self.add_lines([pack.data["options"]["pattern"].format(*values) for values in pack.data["options"]["features"]])
    def set(self, objectives = []):
        names = [name.split(" ")[0] for name in objectives if name.split(" ")[1] == "trigger"]
        self.add_lines(["scoreboard players " + op[0:].format(name) for op in self.operations for name in names])
        super().set()

class Built(SelfTaggedFunction):
    def __init__(self, pack):
        today = datetime.today()
        date_str = today.strftime('%Y-%m-%d')
        day_of_year = today.timetuple().tm_yday
        message = json.dumps(['',
            {
                'text': date_str,
                'color': colors[day_of_year%len(colors)]
            },
            {
                'text': f' | {pack.name}',
                'color': 'white'
            }
        ])
        super().__init__(pack, 'built', f'tellraw @s {message}', 'main')
