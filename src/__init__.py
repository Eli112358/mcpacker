from mcpack import (DataPack, Advancement, Recipe)
import copy
import json

from .functions import *
from .items import *

alphabet_keys = 'abcdefghi'
get_pool = lambda rolls=1, entries=[]: copy.deepcopy({'rolls': rolls, 'entries': entries})
get_entry = lambda type='item', name=resolve('stone'): copy.deepcopy({'type': type, 'name': name})
get_range = lambda min=0, max=1: copy.deepcopy({'min': min, 'max': max})
set_multiple = lambda a_dict, keys, get_value: [set_dict(a_dict, key, get_value(key)) for key in keys]
def set_dict(a_dict, key, value): a_dict[key] = value

class DataPacker(DataPack):
    def __init__(self, name, description, auto_process_data=True, progress_logging=True):
        super().__init__(name, description)
        self.data = self.get_data(self.name)
        self.tag = GlobalName(self.name)
        self.functions = Functions()
        self.functions['tick'] = Tick(self)
        self.progress_logging = progress_logging
        if auto_process_data: self.process_data()
        if self.progress_logging: print('DataPacker Initialized.')
    def add_pool(self, path, pool):
        self.copy_loot_table(path).pools.append(pool)
    def copy_loot_table(self, path):
        my_tables = self['minecraft'].loot_tables
        get_tables = lambda pack: pack['minecraft'].loot_tables
        [self.set(resolve(path), copy.deepcopy(get_tables(pack)[path])) for name, pack in self.packs.items() if path in get_tables(pack) and not path in my_tables]
        return my_tables[path]
    def dump(self):
        if self.progress_logging: print('[dump] Starting...')
        def functions(): self.functions.set(self)
        def recipes(): self.recipes()
        try: functions() or recipes()
        except KeyError: pass
        Built(self).set()
        super().dump('out', overwrite=True)
        if self.progress_logging: print('[dump] Complete.')
    def get_data(self, name):
        try:
            with open(f'data/{name}.json') as json_data: return json.load(json_data)
        # data file is optional: return empty dict if it does not exist
        except FileNotFoundError as fnf: return {}
        # but still catch JSONDecodeError
        except json.decoder.JSONDecodeError as jde:
            exit(f'(in {data_file}) {jde.msg}: line {jde.lineno} column {jde.colno}')
    def init_root_advancement(self, icon, description, background='stone'):
        self.set('root', Advancement(
            display={
                'icon': get_ingredient(self, icon),
                'title': get_name(self.name),
                'description': description,
                'background': resolve(f'textures/blocks/{background}.png')
            },
            criteria={'never': {'trigger': resolve('impossible')}}
        ))
    def process_data(self):
        self.__load_dependancies()
        self.functions['load'] = Load(self, self.__try_data('objectives'))
        [self.functions.add(relpath) for relpath in self.__try_data('functions')]
    def recipes(self):
        data = self.__try_data('recipes')
        if not data: return
        root = Advancement(
            display={'icon': get_ingredient(self, 'piston')},
            criteria={'impossible': {'trigger': resolve('impossible')}}
        )
        set_multiple(root.display, ['title', 'description'], lambda key: 'Recipe root')
        self.set('recipes/root', root)
        self.functions['tick'].add_text(f'advancement revoke @a from {resolve("recipes/root", self)}\n')
        for path, data in data.items():
            shaped = len(data) == 3
            icon_id = data[0][1]
            recipe = Recipe(
                type='crafting_shapeless',
                group=self.tag.suffix(path[:path.index('/')]),
                result={'item': resolve(data[0][1]), 'count': data[0][0]}
            )
            if shaped:
                recipe.type = 'crafting_shaped'
                recipe.pattern = data[2]
                recipe.key = {}
                [set_dict(recipe.key, alphabet_keys[i], get_ingredient(self, data[1][i])) for i in range(len(data[1]))]
            else:
                recipe.ingredients = [get_ingredient(self, id) for id in data[1]]
            self.set(path, recipe)
            if 'recipe_advancement' in self.data and self.data['recipe_advancement']:
                advancement = Advancement(
                    parent=resolve('recipes/root', self),
                    rewards={'recipes': [resolve(path, self)]},
                    display={'icon': get_ingredient(self, icon_id), 'hidden': True},
                    criteria={'have_items': {'trigger': resolve('inventory_changed'), 'conditions': {}}}
                )
                set_multiple(advancement.display, ['title', 'description'], lambda key: 'Craftable '+get_name(icon_id))
                set_multiple(advancement.display, ['announce_to_chat', 'show_toast'], lambda key: False)
                advancement.criteria['have_items']['conditions']['items'] = [get_ingredient(self, value) for value in data[1]]
                self.set('recipes/'+path, advancement)
    def set(self, path, value, vanilla=False):
        self[path if ':' in path else resolve(path, self)] = value
    def __load_dependancies(self):
        if not 'dependancies' in self.data: return
        self.packs = {}
        def load(name):
            if self.progress_logging: print(f"[dependancies] Loading '{name}'...")
            return DataPack.load('out/'+name)
        set_multiple(self.packs, self.data['dependancies'], load)
        if self.progress_logging: print('[dependancies] Complete.')
    def __try_data(self, name):
        try: return self.data[name]
        except KeyError: return []
        except TypeError: return []

class GlobalName(str):
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return self.name
    def suffix(self, suffix):
        return GlobalName('_'.join([self.name, suffix]))
