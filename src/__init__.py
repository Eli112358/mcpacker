import logging
import sys
import time
import zipfile
from collections import OrderedDict

import dill as pickle
from mcpack import (
    Advancement,
    DataPack,
    FunctionTag,
    LootTable,
    Recipe,
    Structure,
)

from .functions import *
from .items import *
from .namespaced import Namespaced
from .order_form import OrderForm
from .shared_trigger import SharedTrigger

alphabet_keys = 'abcdefghi'
max_load_milliseconds = get_env_var('max_load_milliseconds', 500)


def fix_logger(log, level=0):
    if not log.handlers:
        log.propagate = False
        log.addHandler(logging.StreamHandler(sys.stdout))
        log.handlers[0].setFormatter(logging.Formatter(f'[{log.name}] %(message)s'))
    if level:
        log.setLevel(level)
    return log


def get_logger(parent, _name):
    return fix_logger(parent.getChild(_name), parent.level)


def duration(start, end):
    return f'Took {int((end - start) * 1000)} milliseconds'


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
            display['background'] = str(Namespaced(f'textures/blocks/{bg}.png'))
        return display

    @staticmethod
    def criteria(_name, trigger, conditions=None):
        criteria = {f'{_name}': {'trigger': trigger}}
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
        return {_type: [self.pack.namespaced(_path) for _path in paths] for _type, paths in data}


class DataPacker(DataPack):
    data_errors = {
        'KeyError': 'Key not found in data: %s',
        'TypeError': 'Type mismatch in data: %s'
    }
    data_defaults = {
        'dependencies': [],
        'function_code': {},
        'function_tags': [],
        'functions': [],
        'objectives': [],
        'options': {},
        'order_forms': {},
        'recipe_advancement': False,
        'recipes': [],
        'shared_triggers': {}
    }
    defaults = {
        'auto_process_data': True,
        'compress': True,
        'dependencies_dir': pathlib.Path('out'),
        'log_level': 0,
        'output_path': pathlib.Path('out'),
        'overwrite': True,
        'required_data': [],
        'use_pickle': True
    }

    def __init__(self, _name, description, **kwargs):
        super().__init__(_name, description)
        self.adv = AdvancementArgs(self)
        self.log = fix_logger(logging.getLogger(self.name))
        self.structures_to_load = {}
        self.tag = GlobalName(self.name)
        for key, value in DataPacker.defaults.items():
            setattr(self, key, kwargs.get(key, value))
        self.log.setLevel(self.log_level)
        self.data = self.load_data(self.name)
        self.functions = Functions()
        self.functions['tick'] = Tick(self)
        self.shared_triggers = {}
        if self.auto_process_data:
            self.log.debug('Auto processing data')
            self.process_data()
        self.log.info('Initialized')

    def __getitem__(self, item):
        if item in self.namespaces:
            return self.namespaces[item]
        ns_item = self.namespaced(item)
        obj_type = ns_item.value.parts[0]
        obj_dict = getattr(self.namespaces[ns_item.namespace], obj_type)
        if len(ns_item.value.parts) == 1:
            return obj_dict
        return obj_dict[str(ns_item.value.relative_to(obj_type))]

    def __setitem__(self, key, value):
        super().__setitem__(str(self.namespaced(key)), value)

    def add_to_tag(self, tag_path, function_path):
        self.create_function_tag(tag_path).values.append(self.namespaced(function_path))

    def create_function_tag(self, path):
        if path.str not in self[path.type_only('function_tags')]:
            self[path] = FunctionTag()
        return self[path.typed('function_tags')]

    def add_pool(self, _path, pool):
        get_logger(self.log, 'add_pool').debug(_path)
        self.get_kind(_path, LootTable, True).pools.append(pool)

    @deprecated(version='0.11.0', reason='Generalized to get_kind')
    def copy_loot_table(self, _path):
        return self.get_kind(_path, LootTable, True)

    def dump(self, **kwargs):
        log = get_logger(self.log, 'dump')
        log.info('Starting...')
        lambdas = OrderedDict([
            ('shared_triggers', lambda: [trigger.set() for _, trigger in self.shared_triggers.items()]),
            ('functions', lambda: self.functions.set(self)),
            ('recipes', lambda: self.recipes())
        ])
        for _name, _lambda in lambdas.items():
            log.debug(_name.capitalize())
            try:
                _lambda()
            except KeyError as k_err:
                log.debug('Key not found: %s', k_err)
        Built(self).set()
        log.debug('super')
        output_path = kwargs.get('output_path', self.output_path)
        overwrite = kwargs.get('overwrite', self.overwrite)
        super().dump(output_path, overwrite)
        log.info('Complete')
        self.compress_zip()

    def compress_zip(self):
        if not self.compress:
            return
        log = get_logger(self.log, 'zip')
        log.info('Starting...')
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
        log.info('Complete')

    def load_data(self, _name):
        log = get_logger(self.log, 'data')
        data_path = pathlib.Path(f'data/{_name}.json')
        try:
            with open(data_path) as json_data:
                return json.load(json_data)
        except FileNotFoundError as fnf_err:
            if _name in self.required_data:
                log.warning('%s: %s', fnf_err.strerror, str(data_path))
        except json.decoder.JSONDecodeError as jde:
            log.warning('(%s) %s: line %s column %s', str(data_path), jde.msg, jde.lineno, jde.colno)
        return {}

    def namespaced(self, path):
        return Namespaced(path, self.name)

    def init_root_advancement(self, icon, description, background='stone'):
        self['root'] = Advancement(
            display=self.adv.display(icon, self.name, description, background),
            criteria=self.adv.criteria_impossible()
        )

    @deprecated(version='0.11.0', reason='Generalized to get_kind')
    def get_loot_table(self, _path):
        return self.get_kind(_path, LootTable)

    def get_kind(self, path, kind, do_copy=False):
        kind_single = kind.folder
        if kind_single[-1] == 's':
            kind_single = kind_single[:-1]
        log = get_logger(self.log, f'get_{kind_single}')
        log.debug(path)
        ns_path = Namespaced(path)
        log.debug(str(ns_path))
        for name, pack in self.packs.items():
            log.debug(name)
            if ns_path.namespace in pack.namespaces and ns_path.str in pack[ns_path.type_only(kind.folder)]:
                log.debug(f'Found in {name}')
                if do_copy:
                    self[ns_path] = copy.deepcopy(pack[ns_path.typed(kind.folder)])
                    return self[ns_path]
                return pack[ns_path.typed(kind.folder)]
        display = kind_single.replace('_', ' ').capitalize()
        self.log.warning(f'{display} not found: {str(ns_path)}')
        return kind()

    @classmethod
    def cast(cls, _pack):
        self = cls(_pack.name, _pack.description)
        for attr in ['pack_format', 'namespaces']:
            setattr(self, attr, getattr(_pack, attr))
        return self

    @classmethod
    def load(cls, _name, logger=None, use_pickle=True, load_dir=None):
        log = get_logger(logger, 'load')
        if not load_dir:
            load_dir = pathlib.Path('out')
        src = load_dir / _name
        if use_pickle:
            src = pathlib.Path('pickle') / (_name + '.pickle')
            self = cls.unpickle(src, log)
            if self is not None:
                return self
        src_zip = f'{src}.zip'
        if zipfile.is_zipfile(src_zip):
            if not os.path.exists(src):
                zipfile.ZipFile(src_zip).extractall(src)
        log.info(f"Loading '{_name}' ...")
        start = time.time()
        self = DataPacker.cast(DataPack.load(src))
        end = time.time()
        log.info(duration(start, end))
        if (end - start) * 1000 > max_load_milliseconds and use_pickle:
            log.info(f"Pickling '{self.name}' as it took too long to load...")
            self.pickle(pathlib.Path('pickle') / (self.name + '.pickle'), log)
        return self

    def pickle(self, path, logger):
        log = get_logger(logger, 'pickle')
        structures_present = any([namespace.structures for ns_name, namespace in self.namespaces.items()])
        saved_structures = {}
        if structures_present:
            log.info('Saving structures to separate lists...')
            start = time.time()
            for ns_name, namespace in self.namespaces.items():
                self.structures_to_load[ns_name] = []
                saved_structures[ns_name] = {}
                for struct_path, structure in namespace.structures.items():
                    self.structures_to_load[ns_name].append(struct_path)
                    saved_structures[ns_name][struct_path] = structure
            end = time.time()
            log.info(duration(start, end))
            log.info('Removing structures...')
            start = time.time()
            for ns, structures in self.structures_to_load.items():
                for struct_path in structures:
                    self.namespaces[ns].structures.pop(struct_path)
            end = time.time()
            log.info(duration(start, end))
        log.info('Writing pickle file...')
        start = time.time()
        pickle.dump(self, open(path, 'wb'))
        end = time.time()
        log.info(duration(start, end))
        if structures_present:
            log.info('Restoring structures...')
            start = time.time()
            for s_path, structure in saved_structures.items():
                self[s_path] = structure
            end = time.time()
            log.info(duration(start, end))

    @classmethod
    def unpickle(cls, path, logger):
        log = get_logger(logger, 'unpickle')
        if not os.path.exists(path):
            log.debug(f'File not found: {str(path)}')
            return None
        log.info('Found pickle, unpickling...')
        start = time.time()
        self = pickle.load(open(path, 'rb'))
        end = time.time()
        log.info(duration(start, end))
        if self.structures_to_load:
            log.info('Loading structures...')
            start = time.time()
            data_dir = self.dependencies_dir / self.name / 'data'
            for ns, paths in self.structures_to_load.items():
                for struct_path in paths:
                    full_struct_path = data_dir / ns / 'structures' / (struct_path + '.nbt')
                    self[f'{ns}:{struct_path}'] = Structure.load(full_struct_path)
            end = time.time()
            log.info(duration(start, end))
        return self

    def order_forms(self, get_item, villager):
        order_forms = {key: OrderForm.parse(data, get_item) for key, data in self.get_data('order_forms').items()}
        for action in ['completed', 'purchase', 'progress']:
            for _, form in order_forms.items():
                getattr(form, action)(villager)

    def process_data(self):
        for _name, data in self.get_data('shared_triggers').items():
            self.shared_triggers[_name] = SharedTrigger(self, _name, **data)
        self.__load_dependencies()
        for tag in self.get_data('function_tags'):
            self[tag] = FunctionTag()
        self.functions['load'] = Load(self, self.get_data('objectives'))
        function_data = self.get_data('functions')
        if function_data:
            for rel_path in function_data:
                self.functions.add(rel_path)

    def recipes(self):
        recipes = self.get_data('recipes')
        if not recipes:
            return
        self['recipes/root'] = Advancement(
            display=self.adv.display('piston', 'Recipe root', 'Recipe root'),
            criteria=self.adv.criteria_impossible()
        )
        self.functions['tick'].add_text(f'advancement revoke @a from {self.namespaced("recipes/root")}\n')
        for _path, data in recipes.items():
            shaped = len(data) - 2
            icon_id = data[0][1]
            self[_path] = Recipe(
                type='crafting_shape' + ['less', 'd'][shaped],
                group=self.tag.suffix(_path[:_path.index('/')]),
                result={'item': str(Namespaced(data[0][1])), 'count': data[0][0]},
                pattern=data[2] if shaped else None,
                key={alphabet_keys[i]: get_ingredient(self, d) for i, d in enumerate(data[1])} if shaped else None,
                ingredients=[get_ingredient(self, _id) for _id in data[1]] if not shaped else None
            )
            if self.get_data('recipe_advancement'):
                title = 'Craftable ' + get_name(icon_id)
                advancement = Advancement(
                    parent=self.namespaced('recipes/root').value,
                    rewards=self.adv.rewards([['recipes', [_path]]]),
                    display=self.adv.display(icon_id, title, title),
                    criteria=self.adv.criteria_have_items(data[1])
                )
                for key in ['announce_to_chat', 'hidden', 'show_toast']:
                    advancement.display.setdefault(key, '_' not in key)
                self['recipes/' + _path] = advancement

    def __load_dependencies(self):
        log = get_logger(self.log, 'dependencies')
        self.packs = OrderedDict()
        dependencies = self.get_data('dependencies')
        self.packs.setdefault('self', self)
        for key in dependencies:
            self.packs.setdefault(key, DataPacker.load(key, log, self.use_pickle, self.dependencies_dir))
        if dependencies:
            log.info('Complete')

    def get_data(self, _name):
        try:
            self.data.setdefault(_name, DataPacker.data_defaults[_name])
            return self.data[_name]
        except (KeyError, TypeError) as e:
            self.log.debug(DataPacker.data_errors[e.__class__.__name__], e)
            return DataPacker.data_defaults[_name]


class GlobalName(str):
    def __init__(self, _name):
        super().__init__()
        self.name = _name

    def __str__(self):
        return self.name

    def suffix(self, suffix):
        return GlobalName('_'.join([self.name, suffix]))
