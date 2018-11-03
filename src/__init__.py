from mcpack import (DataPack, Advancement, Recipe)
from mcpacker.functions import *
from mcpacker.items import *
import copy
import json

class DataPacker(DataPack):
    def __init__(self, name, description):
        super().__init__(name, description)
        data_file = f'src/{self.name}.json'
        try:
            with open(data_file) as json_data:
                self.data = json.load(json_data)
        except Exception as e:
            print('Failed to load data file: ' + data_file)
    def tag(self, tag):
        return f'{self.name}_{tag}'
    def set(self, path, value, vanilla = False):
        this_path = resolve(path, self)
        if ':' in path:
            this_path = path
        self[this_path] = value
    def require(self, names):
        self.dependancies = {}
        for name in names:
            self.dependancies[name] = DataPack.load(f'out/{name}').namespaces['minecraft'].loot_tables
    def copy_loot_table(self, path):
        for name, pack in self.dependancies.items():
            if path in pack and not path in self['minecraft'].loot_tables:
                self.set(f'minecraft:{path}', copy.deepcopy(pack[path]))
        return self['minecraft'].loot_tables[path]
    def add_pool(self, path, pool):
        self.copy_loot_table(path).pools.append(pool)
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
            self.set(f'recipes/{path}', advancement)
    def dump(self):
        try:
            self.load.set(self)
        except Exception as e:
            pass
        try:
            self.tick.set(self, self.objectives)
        except Exception as e:
            pass
        try:
            self.tick.set(self)
        except Exception as e:
            pass
        try:
            self.functions.set(self)
        except Exception as e:
            pass
        Built().set(self)
        super().dump('out', overwrite=True)