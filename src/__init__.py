import copy
import json

from mcpack import (DataPack, Advancement, Recipe)

from .functions import *
from .items import *

alphabet_keys = 'abcdefghi'

class Advancement_Args():
    def __init__(self, pack):
        self.pack = pack
    def display(self, id, title, desc, bg=None):
        display = {
            'icon': get_ingredient(self.pack, id),
            'title': get_name(title),
            'description': desc
        }
        if bg: display['background'] = resolve(f'textures/blocks/{bg}.png')
        return display
    def criteria(self, name, trigger, conditions=None):
        criteria = {f'{name}': {'trigger': resolve(trigger)}}
        if conditions: criteria['conditions'] = conditions
        return criteria
    def criteria_impossible(self):
        return self.criteria('never', 'impossible')
    def criteria_item(self, name, trigger, id):
        return self.criteria(name, trigger, {'item': get_ingredient(self.pack, id)})
    def criteria_have_items(self, ids):
        return self.criteria('have_items', 'inventory_changed', {'items': [get_ingredient(self.pack, id) for id in ids]})
    def rewards(self, data):
        return {type: [resolve(path, self.pack) for path in paths] for type,paths in data}


class DataPacker(DataPack):
    def __init__(self, name, description, auto_process_data=True, progress_logging=True):
        super().__init__(name, description)
        self.data = self.get_data(self.name)
        self.tag = GlobalName(self.name)
        self.functions = Functions()
        self.functions['tick'] = Tick(self)
        self.adv = Advancement_Args(self)
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
        file = f'data/{name}.json'
        try:
            with open(file) as json_data: return json.load(json_data)
        # data file is optional: return empty dict if it does not exist
        except FileNotFoundError as fnf: return {}
        # but still catch JSONDecodeError
        except json.decoder.JSONDecodeError as jde:
            exit(f'(in {file}) {jde.msg}: line {jde.lineno} column {jde.colno}')
    def init_root_advancement(self, icon, description, background='stone'):
        self.set('root', Advancement(display=self.adv.display(icon, self.name, description, background), criteria=self.adv.criteria_impossible()))
    def process_data(self):
        self.__load_dependancies()
        self.functions['load'] = Load(self, self.__try_data('objectives'))
        [self.functions.add(relpath) for relpath in self.__try_data('functions')]
    def recipes(self):
        recipes = self.__try_data('recipes')
        if not recipes: return
        self.set('recipes/root', Advancement(display=self.adv.display('piston', 'Recipe root', 'Recipe root'), criteria=self.adv.criteria_impossible()))
        self.functions['tick'].add_text(f'advancement revoke @a from {resolve("recipes/root", self)}\n')
        for path,data in recipes.items():
            shaped = len(data) - 2
            icon_id = data[0][1]
            self.set(path, Recipe(
                type='crafting_shape'+['less','d'][shaped],
                group=self.tag.suffix(path[:path.index('/')]),
                result={'item': resolve(data[0][1]), 'count': data[0][0]},
                pattern=data[2] if shaped else None,
                key={alphabet_keys[i]: get_ingredient(self, d) for i,d in enumerate(data[1])} if shaped else None,
                ingredients=[get_ingredient(self, id) for id in data[1]] if not shaped else None
            ))
            if self.__try_data('recipe_advancement'):
                title = 'Craftable '+get_name(icon_id)
                advancement = Advancement(
                    parent=resolve('recipes/root', self),
                    rewards=self.adv.rewards([['recipes', [path]]]),
                    display=self.adv.display(icon_id, title, title),
                    criteria=self.adv.criteria_have_items(data[1])
                )
                [advancement.display.setdefault(key, not '_' in key) for  key in ['announce_to_chat', 'hidden', 'show_toast']]
                self.set('recipes/'+path, advancement)
    def set(self, path, value, vanilla=False):
        self[path if ':' in path else resolve(path, self)] = value
    def __load_dependancies(self):
        if not 'dependancies' in self.data: return
        self.packs = {}
        def load(name):
            if self.progress_logging: print(f"[dependancies] Loading '{name}'...")
            return DataPack.load('out/'+name)
        [self.packs.setdefault(key, load(key)) for key in self.data['dependancies']]
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
