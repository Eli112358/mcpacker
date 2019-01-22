from mcpack import (DataPack, Advancement, Recipe)
from mcpacker.functions import *
from mcpacker.items import *
import copy
import json

alphabet_keys = 'abcdefghi'

class DataPacker(DataPack):
    def __init__(self, name, description, auto_process_data = True):
        super().__init__(name, description)
        self.data = self.get_data(self.name)
        self.tag = GlobalName(self.name)
        self.tick = Tick(self)
        if auto_process_data:
            self.process_data()
    def add_pool(self, path, pool):
        self.copy_loot_table(path).pools.append(pool)
    def copy_loot_table(self, path):
        for name, pack in self.packs.items():
            tables = pack['minecraft'].loot_tables
            if path in tables and not path in self['minecraft'].loot_tables:
                self.set(f'minecraft:{path}', copy.deepcopy(tables[path]))
        return self['minecraft'].loot_tables[path]
    def dump(self):
        def functions(): self.functions.set(self)
        def load(): self.load.set()
        def tick(): self.tick.set()
        def tick_1(): self.tick.set(self.data['objectives'])
        def recipes(): self.recipes()
        try: functions() or load() or tick_1() or tick() or recipes()
        except AttributeError: pass
        except KeyError: pass
        Built(self).set()
        super().dump('out', overwrite=True)
    def get_data(self, name):
        data_file = f'data/{name}.json'
        try:
            with open(data_file) as json_data:
                return json.load(json_data)
        # data file is optional: ignore error if it does not exist
        except FileNotFoundError as fnf: pass
        # but still catch JSONDecodeError
        except json.decoder.JSONDecodeError as jde:
            msg,line,col = jde.msg,jde.lineno,jde.colno
            print(f'(in {data_file}) {msg}: line {line} column {col}')
            exit()
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
    def process_data(self):
        self.__load_dependancies()
        self.functions = Functions(self.__try_data('functions'))
        self.load = Load(self, self.__try_data('objectives'))
    def recipes(self):
        self.set('recipes/root', Advancement(
            display = {
                'icon': get_ingredient(self, 'piston'),
                'title': 'Recipe root',
                'description': 'Recipe root'
            },
            criteria = {
                'impossible': {
                    'trigger': resolve('impossible')
                }
            }
        ))
        self.tick.add_text(f'advancement revoke @a from {resolve("recipes/root", self)}\n')
        for path, data in self.data['recipes'].items():
            shaped = len(data) == 3
            recipe = Recipe(
                type = 'crafting_shapeless',
                group = f"{self.tag.suffix(path[:path.index('/')])}",
                result = {'item': resolve(data[0][1]), 'count': data[0][0]}
            )
            if shaped:
                recipe.type = 'crafting_shaped'
                recipe.pattern = data[2]
                recipe.key = {}
            else:
                recipe.ingredients = []
            icon_id = data[0][1]
            advancement = Advancement(
                parent = resolve('recipes/root', self),
                rewards = {'recipes': [resolve(path, self)]},
                display = {
                    'icon': get_ingredient(self, icon_id),
                    'title': f'Craftable {get_name(icon_id)}',
                    'description': f'Craftable {get_name(icon_id)}',
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
            for i in range(len(data[1])):
                entry = get_ingredient(self, data[1][i])
                if shaped:
                    recipe.key[alphabet_keys[i]] = entry
                else:
                    recipe.ingredients.append(entry)
                advancement.criteria['have_items']['conditions']['items'].append(entry)
            self.set(path, recipe)
            if 'recipe_advancement' in self.data:
                if self.data['recipe_advancement']:
                    self.set(f'recipes/{path}', advancement)
    def set(self, path, value, vanilla = False):
        this_path = resolve(path, self)
        if ':' in path:
            this_path = path
        self[this_path] = value
    def __load_dependancies(self):
        data = self.__try_data('dependancies')
        self.packs = {}
        for name in data:
            self.packs[name] = DataPack.load(f'out/{name}')
    def __try_data(self, name):
        try: return self.data[name]
        except KeyError: return []

class GlobalName(object):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name
    def suffix(self, suffix):
        return self.__class__(f'{self.name}_{suffix}')
