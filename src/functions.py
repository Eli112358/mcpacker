from datetime import datetime

from mcpack import Function

from .items import *

colors = get_pkg_data('colors.json')['text']


class FunctionWrapper:
    def __init__(self, body=""):
        self.function = Function(body)

    def add_text(self, text):
        self.function.body += text

    def add_lines(self, lines):
        self.add_text('\n'.join(lines) + ('\n' if len(lines) else ""))

    def add_indexed(self, size, text):
        self.add_lines([text.format(i) for i in range(size)])

    def set(self, _pack, _path, callback=None):
        if not len(self.function.body):
            return
        _pack[_path] = self.function
        if callback:
            callback()


class Functions(dict):
    def add(self, rel_path, body=None):
        if body is None:
            body = ['']
        self[rel_path] = FunctionWrapper("\n".join(body))

    def add_data(self, _pack):
        def data_lines(_path, _object, entry, i):
            return _pack.data['function_templates'][_path]['template'].format(*data_format(_object, entry, i))

        def data_format(_object, entry, i):
            return [i] + entry[1:] if 'iterator' in _object else entry

        def data_range(_object, entry):
            return entry[0] if 'iterator' in _object else 1

        def data_lines1(_object, _path, entry):
            return [data_lines(_path, _object, entry, i) for i in range(data_range(_object, entry))]
        for _path, _object in _pack.data['function_templates'].items():
            for _entry in _object['data']:
                self[_path].add_lines(data_lines1(_object, _path, _entry))

    def load(self, _pack):
        if 'function_code' not in _pack.data:
            return
        for _path, lines in _pack.data['function_code'].items():
            self[_path].add_lines(lines)

    def set(self, _pack):
        for _path, func in self.items():
            func.set(_pack, resolve(_path, _pack))


class SelfTaggedFunction(FunctionWrapper):
    def __init__(self, _pack, rel_path, body="", _namespace='minecraft'):
        self.pack = _pack
        self.rel_path = rel_path
        self.namespace = _namespace
        self.full_path = resolve(rel_path, _pack)
        super().__init__(body)

    def set(self, _pack=None, _path=None, **kwargs):
        def callback():
            tag_path = resolve(self.rel_path, namespace=kwargs.get('tag_space', self.pack.name))
            self.pack.add_to_tag(tag_path, self.rel_path)
        super().set(self.pack, self.full_path, callback)


class Load(SelfTaggedFunction):
    def __init__(self, _pack, objectives=None):
        super().__init__(_pack, 'load')
        if objectives is None:
            objectives = []
        self.add_lines([f'scoreboard objectives add {_name}' for _name in objectives])

    def set(self, pack=None, path=None, **kwargs):
        super().set(tag_path='minecraft')


class Tick(SelfTaggedFunction):
    operations = [
        'set @a[scores={{{0}=1..}}] {0} 0',
        'add @a {} 0',
        'enable @a {}'
    ]

    def __init__(self, _pack, body=''):
        super().__init__(_pack, 'tick', body)
        if 'options' in _pack.data:
            lines = [_pack.data['options']['pattern'].format(*values) for values in _pack.data['options']['features']]
            self.add_lines(lines)

    def set(self, _pack=None, _path=None, **kwargs):
        objectives = [] if 'objectives' not in _pack.data else _pack.data['objectives']
        names = [_name.split(' ')[0] for _name in objectives if _name.split(' ')[1] == 'trigger']
        self.add_lines(['scoreboard players ' + op[0:].format(_name) for op in self.operations for _name in names])
        super().set(tag_path='minecraft')


class Built(SelfTaggedFunction):
    def __init__(self, _pack):
        today = datetime.today()
        tellraw = 'tellraw @s ' + json.dumps([
            '',
            {
                'text': today.strftime('%Y-%m-%d'),
                'color': colors[today.timetuple().tm_yday % len(colors)]
            },
            {
                'text': f' | {_pack.name}',
                'color': 'white'
            }
        ])
        super().__init__(_pack, 'built', tellraw, 'main')
