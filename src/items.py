import os
import copy
import re

server_name = os.environ.get('minecraft_server_name', '')

wood_types = [
    'oak',
    'spruce',
    'birch',
    'jungle',
    'acacia',
    'dark_oak'
]

def escape(str):
    return str.replace('\\', '\\\\').replace('"', '\\"')
def get_name(name):
    words = re.sub('[_ ]', ' ', name).split(' ')
    for i in range(len(words)):
        words[i] = words[i].capitalize()
    return ' '.join(words)
def resolve(path, pack = None, namespace = 'minecraft'):
    try:
        namespace = pack.name
    except Exception as e:
        pass
    return f'{namespace}:{path}'
def get_ingredient(pack, name):
    if name[0] != '#':
        return {'item': resolve(name)}
    if name[1] != '#':
        return {'tag': resolve(name[1:])}
    return {'tag': resolve(name[2:], pack)}
def get_tag_entry(pack, name):
    if name[1] == '#':
        return name.replace('##', f'#{pack.name}:')
    if name[0] == '#':
        return '#' + resolve(name[1:])
    return resolve(name)

class NbtList(object):
    def __init__(self, name, pattern = '', data = []):
        self.name = name
        self.pattern = pattern
        self.data = data[0:]
    def dump(self):
        list = []
        for value in self.data:
            entry = self.pattern[0:]
            for i in range(len(value)):
                entry = entry.replace(f'{{value[{i}]}}', f'{value[i]}')
            list.append(entry)
        return self.name + ':[' + ','.join(list) + ']'

class NbtObject(object):
    def __init__(self, name, values = [], children = []):
        self.name = name
        self.values = values[0:]
        self.children = children[0:]
    def dump(self):
        result = self.name + ':{'
        list = []
        if self.values:
            result += ','.join(self.values)
        if self.values and self.children:
            result += ','
        for child in self.children:
            list.append(child.dump())
        result += ','.join(list)
        result += '}'
        return result

class ItemDisplay(NbtObject):
    def __init__(self, custom_name, lore = [], values = []):
        super().__init__('display', values)
        self.custom_name = custom_name
        if lore:
            self.set_lore(lore)
    def set_lore(self, lore):
        self.lore = []
        for value in lore:
            self.lore.append([value])
    def dump(self):
        self.escaped_name = escape(f'"{self.custom_name}"')
        self.values.append(f'Name:"{self.escaped_name}"')
        try:
            self.children.append(NbtList('Lore', '"{value[0]}"', self.lore))
        except AttributeError:
            pass
        return super().dump()

class Enchantments(NbtList):
    def __init__(self, list = [['', 1]], stored = False):
        super().__init__('Enchantments', '{id:"{value[0]}",lvl:{value[1]}}', list)
        if stored:
            self.name = 'Stored' + self.name

class ItemNbt(object):
    def __init__(self, display, values = [], objects = []):
        self.display = display
        self.values = values
        self.objects = objects
    def dump(self):
        parts = []
        if self.display:
            parts.append(self.display.dump())
        if self.values:
            parts.append(','.join(self.values))
        for obj in self.objects:
            parts.append(obj.dump())
        return '{' + ','.join(parts) + '}'

class Item(object):
    def __init__(self, id, count = 1, nbt = None):
        self.id = id
        self.count = count
        self.nbt = nbt
    def get_name(self):
        if self.nbt:
            return get_name(self.nbt.display.custom_name)
        return get_name(self.id)
    def stack(self, count):
        item = copy.deepcopy(self)
        item.count = count
        return item
    def loot(self):
        entry = {
            'type': 'item',
            'name': resolve(self.id)
        }
        functions = []
        if self.count > 1:
            functions.append({
                'function': 'set_count',
                'count': self.count
            })
        if self.nbt:
            functions.append({
                'function': 'set_nbt',
                'nbt': self.nbt.dump()
            })
        if len(functions) > 0:
            entry['functions'] = functions
        return entry
    def trade(self):
        result = f'{{id:"minecraft:{self.id}",Count:{self.count}'
        if self.nbt:
            result += ',tag:'
            result += self.nbt.dump()
        return result + '}'

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
    def __init__(self, count, index = 0, value = None):
        if index < 0:
            index += len(self.denominations)
        if value == None:
            value = self.denominations[index]
        lore = ['Official Bank Note']
        if server_name:
            lore[0] += f' of {server_name}'
        display = ItemDisplay(f'{value} Bank Note', lore)
        nbt = ItemNbt(display, [], [Enchantments()])
        super().__init__('paper', count, nbt)

class EnchantedBook(Item):
    def __init__(self, list, display = None):
        super().__init__('enchanted_book', 1, ItemNbt(display, [], [Enchantments(list, True)]))
