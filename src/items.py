import os
import copy
import re
from nbtlib import (parse_nbt, serialize_tag)
from nbtlib.tag import (Compound, List, String)

server_name = os.environ.get('minecraft_server_name', '')
currency_name = os.environ.get('minecraft_currency_name', 'Bank Note')

wood_types = [
    'oak',
    'spruce',
    'birch',
    'jungle',
    'acacia',
    'dark_oak'
]

quote = lambda s: f'"{s}"'
escape = lambda s: s.replace('\\', '\\\\').replace('"', '\\"')
custom_name = lambda name: String(quote(escape(quote(name))))
flatten = lambda name: re.sub('_{2,}', ' ', re.sub('[ .,\'"\\/#!$%^&*;:{}=\-`~()]', '_', name)).lower()
resolve = lambda path, pack=None, namespace='minecraft': f'{pack.name if pack else namespace}:{path}'
get_pool = lambda rolls=1, entries=[]: copy.deepcopy({'rolls': rolls, 'entries': entries})
get_entry = lambda type='item', name=resolve('stone'): copy.deepcopy({'type': type, 'name': name})
get_range = lambda min=0, max=1: copy.deepcopy({'min': min, 'max': max})
def get_name(name):
    words = re.sub('[_ ]', ' ', name).split(' ')
    for i in range(len(words)):
        words[i] = words[i].capitalize()
    return ' '.join(words)
def get_ingredient(pack, name):
    return Switch(2, (lambda i: name[i]=='#'), [
        {'item': resolve(name)},
        {'tag': resolve(name[1:])},
        {'tag': resolve(name[2:], pack)}
    ]).dump()
def get_tag_entry(pack, name):
    return Switch(2, (lambda i: name[i]=='#'), [
        resolve(name),
        ('#' + resolve(name[1:])),
        name.replace('##', f'#{pack.name}:')
    ]).dump()
def set_nbt_list(nbt, name, pattern='', data=[]):
    nbt[name] = List[Compound]([parse_nbt(pattern.format(*value)) for value in data[0:]])
def set_enchantments(nbt, list=[['', 1]], stored=False):
    prefix = 'Stored' if stored else ''
    set_nbt_list(nbt, f'{prefix}Enchantments', '{{id:"{}",lvl:{}}}', list)

class Switch():
    def __init__(self, max, check, cases):
        self.max = max
        self.check = check
        self.cases = cases
    def dump(self):
        return self.cases[sum([self.check(i) for i in range(self.max)])]

class Item():
    def __init__(self, id, count=1, nbt=None):
        self.id = resolve(id)
        self.count = count
        self.nbt = nbt
    def get_name(self):
        if 'display' in self.nbt:
            if 'Name' in self.nbt['display']:
                return get_name(serialize_tag(self.nbt['display']['Name']))
        return get_name(self.id)
    def stack(self, count):
        item = copy.deepcopy(self)
        item.count = count
        return item
    def __get_fixed_nbt(self):
        return re.sub("(?<=:)'|'(?=[,}])", '', serialize_tag(self.nbt, compact=True)).replace('\\\\', '\\')
    def loot(self):
        entry = get_entry(name=self.id)
        entry['functions'] = []
        def add_function(value, name, fname=None):
            fname = fname if fname else f'set_{name}'
            entry['functions'].append({'function': fname, f'{name}': value})
        if self.count > 1:
            add_function(self.count, 'count')
        if self.nbt:
            add_function(self.__get_fixed_nbt(), 'tag', 'set_nbt')
        if len(entry['functions']) == 0:
            entry.pop('functions')
        return entry
    def trade(self):
        return f'id:{quote(self.id)},Count:{self.count}' + (f',nbt:{self.__get_fixed_nbt()}' if self.nbt else '')
    def give(self):
        return self.id + (self.__get_fixed_nbt() if self.nbt else '') + (' '+self.count if self.count > 1  else '')

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
        if value == None:
            value = self.denominations[index]
        lore_suffix = f' of {server_name}' if server_name else ''
        nbt = Compound(dict(display=dict(
            Name=custom_name(f'{value} {currency_name}'),
            Lore=List[String]([f'Official {currency_name}{lore_suffix}'])
        )))
        set_enchantments(nbt)
        super().__init__('paper', count, nbt)

class EnchantedBook(Item):
    def __init__(self, list, display=None):
        nbt = Compound()
        if display:
            nbt['display'] = display
        set_enchantments(nbt, list, True)
        super().__init__('enchanted_book', 1, nbt)
