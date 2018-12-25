from mcpack import (DataPack, Advancement, Recipe)
from mcpacker.functions import *
from mcpacker.items import *
from collections import namedtuple
import copy
import json

class DataPacker(DataPack):
    def __init__(self, name, description):
        super().__init__(name, description)
        data_file = f'data/{self.name}.json'
        try:
            with open(data_file) as json_data:
                self.data = json.load(json_data)
        # data file is optional: ignore error if it does not exist
        except FileNotFoundError as fnf: pass
        # but still catch JSONDecodeError
        except json.decoder.JSONDecodeError as jde:
            msg,line,col = jde.msg,jde.lineno,jde.colno
            print(f'(in {data_file}) {msg}: line {line} column {col}')
            exit()
        try: self.require(self.data['dependancies'])
        except KeyError: pass
        try: self.functions = Functions(self.data['functions'])
        except KeyError: pass
        try: self.load = Load(self, self.data['objectives'])
        except KeyError: pass
        self.tick = Tick(self)
    def add_pool(self, path, pool):
        self.copy_loot_table(path).pools.append(pool)
    def copy_loot_table(self, path):
        for name, pack in self.dependancies.items():
            if path in pack and not path in self['minecraft'].loot_tables:
                self.set(f'minecraft:{path}', copy.deepcopy(pack[path]))
        return self['minecraft'].loot_tables[path]
    def dump(self):
        def functions(): self.functions.set(self)
        def load(): self.load.set()
        def tick(): self.tick.set()
        def tick_1(): self.tick.set(self.data['objectives'])
        try: functions() or load() or tick_1() or tick()
        except AttributeError: pass
        Built(self).set()
        super().dump('out', overwrite=True)
    def init_root_advancement(self, icon, description, background = 'stone'):
        self.set('root', Advancement(
            display = {
                'icon': get_ingredient(self, icon),
                'title': get_name(self.name),
                'description': description,
                'background': resolve(f'textures/blocks/{background}.png')
            },
            criteria = {
                'never': {
                    'trigger': resolve('impossible')
                }
            }
        ))
    def recipes(self):
        for path, data in self.data['recipes'].items():
            recipe = Recipe(
                type = 'crafting_shapeless',
                group = self.tag(path[:path.index('/')]),
                result = {'item': resolve(data[0][1]), 'count': data[0][0]},
                ingredients = []
            )
            item = path[path.index('/')+1:]
            advancement = Advancement(
                parent = resolve('root', self),
                rewards = {'recipes': [resolve(path, self)]},
                display = {
                    'icon': get_ingredient(self, item),
                    'title': f'Craftable {item}',
                    'description': f'Craftable {item}',
                    'show_toast': False,
                    'announce_to_chat': False,
                    'hidden': True
                },
                criteria = {
                    'have_items': {
                        'trigger': resolve('inventory_changed'),
                        'conditions': {'items': []}
                    }
                }
            )
            for item in data[1]:
                recipe.ingredients.append(get_ingredient(self, item))
                advancement.criteria['have_items']['conditions']['items'].append(get_ingredient(self, path[path.index('/')+1:]))
            self.set(path, recipe)
            if 'recipe_advancement' in self.data:
                if self.data['recipe_advancement']:
                    self.set(f'recipes/{path}', advancement)
    def require(self, names):
        self.dependancies = {}
        for name in names:
            self.dependancies[name] = DataPack.load(f'out/{name}').namespaces['minecraft'].loot_tables
    def set(self, path, value, vanilla = False):
        this_path = resolve(path, self)
        if ':' in path:
            this_path = path
        self[this_path] = value
    tag = lambda self, tag: f'{self.name}_{tag}'
