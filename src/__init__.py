import dill as pickle
import pathlib
import time
import zipfile

from mcpack import (DataPack, Advancement, Recipe, Structure)

from .functions import *
from .items import *

max_load_milliseconds = os.environ.get('minecraft_maximum_load_milliseconds', 500)
alphabet_keys = 'abcdefghi'


class AdvancementArgs:
    def __init__(self, _pack):
        self.pack = _pack

    def display(self, _id, title, desc, bg=None):
        display = {
            'icon': get_ingredient(self.pack, _id),
            'title': get_name(title),
            'description': desc
        }
        if bg:
            display['background'] = resolve(f'textures/blocks/{bg}.png')
        return display

    @staticmethod
    def criteria(_name, trigger, conditions=None):
        criteria = {f'{_name}': {'trigger': resolve(trigger)}}
        if conditions:
            criteria[f'{_name}']['conditions'] = conditions
        return criteria

    def criteria_impossible(self):
        return self.criteria('never', 'impossible')

    def criteria_item(self, _name, trigger, _id):
        return self.criteria(_name, trigger, {'item': get_ingredient(self.pack, _id)})

    def criteria_have_items(self, ids):
        return self.criteria('have_items', 'inventory_changed', {
            'items': [get_ingredient(self.pack, _id) for _id in ids]
        })

    def rewards(self, data):
        return {_type: [resolve(_path, self.pack) for _path in paths] for _type, paths in data}


class DataPacker(DataPack, dict, object):
    def __init__(self, _name, description, auto_process_data=True, compress=True,
                 progress_logging=False, required_data=None, use_pickle=True, dependencies_dir=None):
        super().__init__(_name, description)
        self.compress = compress
        self.dependencies_dir = dependencies_dir
        if not dependencies_dir:
            self.dependencies_dir = pathlib.Path('out')
        self.progress_logging = progress_logging
        self.required_data = required_data if required_data else []
        self.structures_to_load = {}
        self.use_pickle = use_pickle
        self.data = self.get_data(self.name)
        self.tag = GlobalName(self.name)
        self.functions = Functions()
        self.functions['tick'] = Tick(self)
        self.adv = AdvancementArgs(self)
        if auto_process_data:
            self.process_data()
        if self.progress_logging:
            print('DataPacker Initialized.')

    def add_pool(self, _path, pool):
        self.copy_loot_table(_path).pools.append(pool)

    def copy_loot_table(self, _path):
        my_tables = self['minecraft'].loot_tables

        def get_tables(_pack):
            return _pack['minecraft'].loot_tables
        for _name, _pack in self.packs.items():
            if _path in get_tables(_pack) and _path not in my_tables:
                self.set(resolve(_path), copy.deepcopy(get_tables(_pack)[_path]))
        return my_tables[_path]

    def dump(self, **kwargs):
        if self.progress_logging:
            print('[dump] Starting...')

        def _functions():
            self.functions.set(self)

        def recipes():
            self.recipes()
        try:
            _functions() or recipes()
        except KeyError:
            pass
        Built(self).set()
        super().dump('out', overwrite=True)
        if self.progress_logging:
            print('[dump] Complete.')
        self.compress_zip()

    def compress_zip(self):
        if not self.compress:
            return
        if self.progress_logging:
            print('[zip] Starting...')
        zip_path = pathlib.Path(f'zip/{self.name}.zip')
        if os.path.exists(zip_path):
            os.remove(zip_path)
        _zip = zipfile.ZipFile(zip_path, 'w')
        out_path = pathlib.Path(f'out/{self.name}')
        for root, dirs, files in os.walk(out_path):
            rel_dir = os.path.relpath(root, out_path)
            for file in files:
                _zip.write(os.path.join(root, file), os.path.join(rel_dir, file))
        _zip.close()
        if self.progress_logging:
            print('[zip] Complete.')

    def get_data(self, _name):
        data_path = pathlib.Path(f'data/{_name}.json')
        try:
            with open(data_path) as json_data:
                return json.load(json_data)
        except FileNotFoundError as fnfe:
            if _name in self.required_data:
                exit(fnfe.strerror + ': ' + str(data_path))
            return {}
        except json.decoder.JSONDecodeError as jde:
            exit(f'(in {data_path}) {jde.msg}: line {jde.lineno} column {jde.colno}')

    def init_root_advancement(self, icon, description, background='stone'):
        self.set('root', Advancement(
            display=self.adv.display(icon, self.name, description, background),
            criteria=self.adv.criteria_impossible()
        ))

    @classmethod
    def cast(cls, _pack):
        self = cls(_pack.name, _pack.description)
        for attr in ['pack_format', 'namespaces']:
            setattr(self, attr, getattr(_pack, attr))
        return self

    @classmethod
    def load(cls, name, progress_logging=False, use_pickle=True, logging_prefix='', load_dir=None):
        if not load_dir:
            load_dir = pathlib.Path('out')
        if use_pickle:
            self = cls.unpickle(pathlib.Path('pickle') / (name + '.pickle'), progress_logging, logging_prefix)
            if self is not None:
                return self
        if progress_logging:
            print(f"[{logging_prefix}load] Loading '{name}' ...")
        start = time.time()
        self = DataPacker.cast(super().load(load_dir / name))
        end = time.time()
        if progress_logging:
            print(f'[{logging_prefix}load] Took {int((end - start) * 1000)} milliseconds')
        if (end - start) * 1000 > max_load_milliseconds and use_pickle:
            if self.progress_logging:
                print(f"[{logging_prefix}load] Pickling '{self.name}' as it took too long to load...")
            self.pickle(pathlib.Path('pickle') / (self.name + '.pickle'))
        return self

    def pickle(self, path, logging_prefix=''):
        structures_present = any([namespace.structures for ns_name, namespace in self.namespaces.items()])
        saved_structures = {}
        if structures_present:
            if self.progress_logging:
                print(f'[{logging_prefix}pickling] Saving structures to separate lists...')
            start = time.time()
            for ns_name, namespace in self.namespaces.items():
                self.structures_to_load[ns_name] = []
                saved_structures[ns_name] = {}
                for struct_path, structure in namespace.structures.items():
                    self.structures_to_load[ns_name].append(struct_path)
                    saved_structures[ns_name][struct_path] = structure
            end = time.time()
            if self.progress_logging:
                print(f'[{logging_prefix}pickling] Took {int((end - start) * 1000)} milliseconds')
                print(f'[{logging_prefix}pickling] Removing structures...')
            start = time.time()
            for ns, structures in self.structures_to_load.items():
                for struct_path in structures:
                    self.namespaces[ns].structures.pop(struct_path)
            end = time.time()
            if self.progress_logging:
                print(f'[{logging_prefix}pickling] Took {int((end - start) * 1000)} milliseconds')
        if self.progress_logging:
            print(f'[{logging_prefix}pickling] Writing pickle file...')
        start = time.time()
        pickle.dump(self, open(path, 'wb'))
        end = time.time()
        if self.progress_logging:
            print(f'[{logging_prefix}pickling] Took {int((end - start) * 1000)} milliseconds')
        if structures_present:
            if self.progress_logging:
                print(f'[{logging_prefix}pickling] Restoring structures...')
            start = time.time()
            for s_path, structure in saved_structures.items():
                self[s_path] = structure
            end = time.time()
            if self.progress_logging:
                print(f'[{logging_prefix}pickling] Took {int((end - start) * 1000)} milliseconds')

    @classmethod
    def unpickle(cls, path, progress_logging=False, logging_prefix=''):
        if not os.path.exists(path):
            return None
        if progress_logging:
            print(f'[{logging_prefix}unpickling] Found pickle, unpickling...')
        start = time.time()
        self = pickle.load(open(path, 'rb'))
        end = time.time()
        if progress_logging:
            print(f'[{logging_prefix}unpickling] Took {int((end - start) * 1000)} milliseconds')
        if self.structures_to_load:
            if progress_logging:
                print(f'[{logging_prefix}unpickling] Loading structures...')
            start = time.time()
            data_dir = self.dependencies_dir / self.name / 'data'
            for ns, paths in self.structures_to_load.items():
                for struct_path in paths:
                    full_struct_path = data_dir / ns / 'structures' / (struct_path + '.nbt')
                    self[f'{ns}:{struct_path}'] = Structure.load(full_struct_path)
            end = time.time()
            if progress_logging:
                print(f'[{logging_prefix}unpickling] Took {int((end - start) * 1000)} milliseconds')
        return self

    def process_data(self):
        self.__load_dependencies()
        self.functions['load'] = Load(self, self.__try_data('objectives'))
        function_data = self.__try_data('functions')
        if function_data:
            [self.functions.add(relpath) for relpath in function_data]

    def recipes(self):
        recipes = self.__try_data('recipes')
        if not recipes:
            return
        self.set('recipes/root', Advancement(
            display=self.adv.display('piston', 'Recipe root', 'Recipe root'),
            criteria=self.adv.criteria_impossible()
        ))
        self.functions['tick'].add_text(f'advancement revoke @a from {resolve("recipes/root", self)}\n')
        for _path, data in recipes.items():
            shaped = len(data) - 2
            icon_id = data[0][1]
            self.set(_path, Recipe(
                type='crafting_shape'+['less', 'd'][shaped],
                group=self.tag.suffix(_path[:_path.index('/')]),
                result={'item': resolve(data[0][1]), 'count': data[0][0]},
                pattern=data[2] if shaped else None,
                key={alphabet_keys[i]: get_ingredient(self, d) for i, d in enumerate(data[1])} if shaped else None,
                ingredients=[get_ingredient(self, _id) for _id in data[1]] if not shaped else None
            ))
            if self.__try_data('recipe_advancement'):
                title = 'Craftable '+get_name(icon_id)
                advancement = Advancement(
                    parent=resolve('recipes/root', self),
                    rewards=self.adv.rewards([['recipes', [_path]]]),
                    display=self.adv.display(icon_id, title, title),
                    criteria=self.adv.criteria_have_items(data[1])
                )
                for key in ['announce_to_chat', 'hidden', 'show_toast']:
                    advancement.display.setdefault(key, '_' not in key)
                self.set('recipes/' + _path, advancement)

    def set(self, _path, value):
        self[_path if ':' in _path else resolve(_path, self)] = value

    def __load_dependencies(self):
        if 'dependencies' not in self.data:
            return
        self.packs = {}
        for key in self.data['dependencies']:
            self.packs.setdefault(key, DataPacker.load(
                key,
                self.progress_logging,
                self.use_pickle,
                'dependencies/',
                self.dependencies_dir
            ))
        if self.progress_logging:
            print('[dependencies] Complete.')

    def __try_data(self, _name):
        try:
            return self.data[_name]
        except KeyError:
            return None
        except TypeError:
            return None


class GlobalName(str):
    def __init__(self, _name):
        super().__init__()
        self.name = _name

    def __str__(self):
        return self.name

    def suffix(self, suffix):
        return GlobalName('_'.join([self.name, suffix]))
