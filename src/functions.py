from datetime import datetime

from mcpack import Function

from .items import *

colors = get_pkg_data('colors.json')['text']


def tellraw(message, target='@s'):
    return f'tellraw {target} {json.dumps(["", *message])}'


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
            return _pack.get_data('function_templates').get(_path).get('template').format(
                *data_format(_object, entry, i)
            )

        def data_format(_object, entry, i):
            return [i] + entry[1:] if 'iterator' in _object else entry

        def data_range(_object, entry):
            return entry[0] if 'iterator' in _object else 1

        def data_lines1(_object, _path, entry):
            return [data_lines(_path, _object, entry, i) for i in range(data_range(_object, entry))]

        for _path, _object in _pack.get_data('function_templates').items():
            for _entry in _object['data']:
                self[_path].add_lines(data_lines1(_object, _path, _entry))

    def load(self, _pack):
        for _path, lines in _pack.get_data('function_code').items():
            self[_path].add_lines(lines)

    def set(self, _pack):
        for _path, func in self.items():
            func.set(_pack, _pack.namespaced(_path))


class SelfTaggedFunction(FunctionWrapper):
    def __init__(self, _pack, rel_path, body='', _namespace='minecraft'):
        self.pack = _pack
        self.path = self.pack.namespaced(rel_path)
        self.tag_path = Namespaced(rel_path, _namespace)
        super().__init__(body)

    def set(self, _pack=None, _path=None, **kwargs):
        def callback():
            self.pack.add_to_tag(self.tag_path, self.path)
        super().set(self.pack, self.path, callback)


class Load(SelfTaggedFunction):
    def __init__(self, _pack, objectives=None):
        super().__init__(_pack, 'load')
        if objectives is None:
            objectives = []
        self.add_lines([f'scoreboard objectives add {_name}' for _name in objectives])


class Tick(SelfTaggedFunction):
    operations = [
        'set @a[scores={{{0}=1..}}] {0} 0',
        'add @a {} 0',
        'enable @a {}'
    ]

    def __init__(self, _pack, body=''):
        super().__init__(_pack, 'tick', body)
        if 'options' in _pack.data:
            self.add_lines([
                _pack.get_data('options').get('pattern').format(*values)
                for values in _pack.get_data('options').get('features')
            ])

    def set(self, _pack=None, _path=None, **kwargs):
        objectives = [] if 'objectives' not in _pack.data else _pack.get_data('objectives')
        names = [_name.split(' ')[0] for _name in objectives if _name.split(' ')[1] == 'trigger']
        self.add_lines(['scoreboard players ' + op[0:].format(_name) for op in self.operations for _name in names])
        super().set()


class Built(SelfTaggedFunction):
    def __init__(self, _pack):
        today = datetime.today()
        body = tellraw([
            {
                'text': today.strftime('%Y-%m-%d'),
                'color': colors[today.timetuple().tm_yday % len(colors)]
            },
            {
                'text': f' | {_pack.name}',
                'color': 'white'
            }
        ])
        super().__init__(_pack, 'built', body, 'main')
