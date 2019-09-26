import copy
import math
import re

from deprecated import deprecated
from nbtlib import (parse_nbt, serialize_tag)
from nbtlib.tag import (Compound, List, String)

from . import Namespaced, get_env_var, get_pkg_data

currency_name = get_env_var('currency_name', 'Bank Note')
server_name = get_env_var('server_name')
stack_data = get_pkg_data('items.json')
wood_types = get_pkg_data('wood.json')['wood_types']

switch_cases = dict(
    ingredients=[
        lambda pack, name: {'item': Namespaced(name)},
        lambda pack, name: {'tag': Namespaced(name[1:])},
        lambda pack, name: {'tag': Namespaced(name[2:], pack)}
    ],
    tag_entries=[
        lambda pack, name: Namespaced(name),
        lambda pack, name: '#' + Namespaced(name[1:]),
        lambda pack, name: name.replace('##', f'#{pack.name}:')
    ]
)


def quote(s):
    return f'"{s}"'


def escape(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def custom_name(name):
    return String(quote(escape(quote(name))))


def flatten(name):
    return re.sub('_{2,}', ' ', re.sub('[- .,\'"/#!$%^&*;:{}=`~()]', '_', name)).lower()


@deprecated(version='0.10.0', reason='Replaced by mcpacker.Path')
def resolve(path, pack=None, namespace='minecraft'):
    if pack is not None:
        return pack.get_path(path)
    return Namespaced(path, namespace)


def get_pool(rolls=1, entries=None):
    if entries is None:
        entries = []
    return copy.deepcopy({'rolls': rolls, 'entries': entries})


def get_entry(_type='item', name=Namespaced('stone')):
    return copy.deepcopy({'type': _type, 'name': name})


def get_range(_min=0, _max=1):
    return copy.deepcopy({'min': _min, 'max': _max})


def get_name(name):
    words = re.sub('[_ ]', ' ', name).split(' ')
    for i in range(len(words)):
        words[i] = words[i].capitalize()
    return ' '.join(words)


def get_ingredient(pack, name):
    return __get_switch_case('ingredients', pack, name)


def get_tag_entry(pack, name):
    return __get_switch_case('tag_entries', pack, name)


def __get_switch_case(key, pack, name):
    return switch_cases[key][name.count('#')](pack, name)


def set_nbt_list(nbt, name, pattern='', data=None, parse=False):
    if data is None:
        data = []
    content = [parse_nbt(pattern.format(*value)) if parse else pattern.format(*value) for value in data[0:]]
    nbt[name] = List[Compound if parse else String](content)


def set_enchantments(nbt, _list=None, stored=False):
    if _list is None:
        _list = [['', 1]]
    prefix = 'Stored' if stored else ''
    set_nbt_list(nbt, f'{prefix}Enchantments', '{{id:"{}",lvl:{}}}', _list, True)


def get_max_stack(_id):
    values = {'non_stackable': 1, 'stack_16': 16}
    for key, value in values.items():
        for entry in stack_data[key]:
            if _id == entry or (re.search('[^$]', entry) and re.search(entry, _id)):
                return value
    return 64


class Item:
    def __init__(self, _id, count=1, nbt=None):
        if count < 1:
            raise ValueError('Count must be more than 0')
        self.id = Namespaced(_id)
        self.count = count
        self.nbt = nbt

    def get_name(self):
        if 'display' in self.nbt:
            if 'Name' in self.nbt['display']:
                return get_name(serialize_tag(self.nbt['display']['Name']))
        return get_name(self.id)

    def stack(self, count=0, clone=True, fixed=True):
        if count == 0:
            return min(self.count, self.stack(fixed=False)) if fixed else get_max_stack(self.id)
        fixed_count = count if not fixed else min(count, self.stack(fixed=False))
        if clone:
            item = copy.deepcopy(self)
            item.count = fixed_count
            return item
        self.count += fixed_count

    def __get_fixed_nbt(self, _nbt=None):
        if not _nbt:
            _nbt = self.nbt
        nbt_copy = copy.deepcopy(_nbt)
        dq = '"'
        if 'display' in nbt_copy.keys():
            if 'Lore' in nbt_copy['display'].keys():
                lore = [f'"\\"{line.strip(dq)}\\""' for line in nbt_copy['display']['Lore']]
                nbt_copy['display']['Lore'] = List[String](lore)
            nbt_copy['display'] = Compound({k: v for k, v in nbt_copy['display'].items()})
        nbt_str = re.sub("(?<=:)'|'(?=[,}])", '', serialize_tag(nbt_copy, compact=True))
        return nbt_str.replace('\\\\', '\\').replace("'", '')

    def loot(self):
        entry = get_entry(name=self.id)
        entry['functions'] = []

        def add_function(value, name, f_name=None):
            f_name = f_name if f_name else f'set_{name}'
            entry['functions'].append({'function': f_name, f'{name}': value})
        if self.count > 1:
            add_function(self.count, 'count')
        if self.nbt:
            add_function(self.__get_fixed_nbt(), 'tag', 'set_nbt')
        if len(entry['functions']) == 0:
            entry.pop('functions')
        return entry

    def trade(self):
        return f'id:{quote(self.id)},Count:{self.stack()}' + ((',tag:' + self.__get_fixed_nbt()) if self.nbt else '')

    def give(self):
        return self.id + self.__get_fixed_nbt() + (' ' + str(self.count) if self.count > 1 else '')


class BankNote(Item):
    denominations = [
        '1 Million',
        '100,000',
        '10,000',
        '1,000',
        '100',
        '10',
        '1',
        '0.1'
    ]

    def __init__(self, count, index=0, value=None):
        if index < 0:
            index += len(self.denominations)
        if value is None:
            value = self.denominations[index]
        lore_suffix = f' of {server_name}' if server_name else ''
        nbt = Compound(dict(display=Compound(dict(
            Name=custom_name(f'{value} {currency_name}'),
            Lore=List[String]([f'Official {currency_name}{lore_suffix}'])
        ))))
        set_enchantments(nbt)
        super().__init__('paper', count, nbt)

    @classmethod
    def parse(cls, value):
        n_denom = len(cls.denominations)
        result = []
        value2 = float(value)
        for i in range(n_denom):
            if value2 == 0:
                break
            pow_ten = 10**(n_denom-i-2)
            magnitude = math.floor(math.log10(value2))
            max_count = round(value2/(int('1'*(magnitude+1))/10), 1)
            next_count = math.floor(value2/(pow_ten/10))
            if next_count % 10 > 0 and \
                    next_count <= 70 and \
                    max_count <= 64:
                continue
            try:
                count = min(math.floor(value2/pow_ten), 64)
                result.append(cls(count, i))
                value2 -= count*pow_ten
            except ValueError:
                pass
        return result


class EnchantedBook(Item):
    def __init__(self, _list, display=None):
        nbt = Compound()
        if display:
            nbt['display'] = display
        set_enchantments(nbt, _list, True)
        super().__init__('enchanted_book', 1, nbt)
