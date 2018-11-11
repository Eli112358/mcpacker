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

class Functions(object):
    def __init__(self, relpaths):
        self.has_set = False
        self.functions = {}
        for relpath in relpaths:
            self.add(relpath)
    def add(self, relpath, body = ''):
        self.functions[relpath] = Function(body)
    def add_text(self, relpath, text):
        self.functions[relpath].body += text
    def add_lines(self, relpath, lines):
        self.add_text(relpath, '\n'.join(lines) + '\n')
    def add_indexed(self, relpath, size, text):
        for i in range(size):
            self.add_text(relpath, text.replace('{i}', f'{i}'))
    def add_data(self, relpath, data, text):
        # TODO: for warps
        pass
    def set(self, pack):
        if self.has_set: return
        for relpath, func in self.functions.items():
            pack[resolve(relpath, pack)] = func
        self.has_set = True

class SelfTaggedFunction(object):
    def __init__(self, pack, relpath, body = '', namespace = 'minecraft'):
        self.has_set = False
        self.pack = pack
        self.relpath = relpath
        self.namespace = namespace
        self.function = Function(body)
        self.fullpath = resolve(relpath, pack)
        pack[resolve(relpath, None, namespace)] = FunctionTag()
    def add_text(self, text):
        self.function.body += text
    def add_lines(self, lines):
        self.add_text('\n'.join(lines) + '\n')
    def add_indexed(self, size, text):
        for i in range(size):
            self.add_text(text.replace('{i}', f'{i}'))
    def set(self):
        if self.has_set: return
        self.pack[self.fullpath] = self.function
        self.pack[self.namespace].function_tags[self.relpath].values.append(self.fullpath)
        self.has_set = True

class Load(SelfTaggedFunction):
    def __init__(self, pack, objectives = []):
        super().__init__(pack, 'load')
        for obj in objectives:
            self.function.body += f'scoreboard objectives add {obj}\n'

class Tick(SelfTaggedFunction):
    def __init__(self, pack, body = ''):
        super().__init__(pack, 'tick', body)
    def set(self, objectives = []):
        names = []
        for obj in objectives:
            if obj.split(' ')[1] == 'trigger':
                names.append(obj.split(' ')[0])
        def add_lines(operation):
            for name in names:
                add_text(f'scoreboard players {operation.replace("{name}", name)}\n')
        add_lines('set @a[scores={{name}=1..}] {name} 0')
        add_lines('add @a {name} 0')
        add_lines('enable @a {name}')
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
