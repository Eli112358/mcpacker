from mcpacker.items import *
from mcpacker.villager import Trade
import os
import copy
import math

server_name = os.environ.get('minecraft_server_name', '')

def last(array):
    return array[len(array)-1]
def get_quantity(count):
    remainder = int(count % 64)
    stacks = int((count - remainder) / 64)
    cases = [
        '',                         # both == 0
        f'{remainder}',             # remainder > 0
        f'{stacks}x64',             # stacks > 0
        f'{stacks}x64 +{remainder}' # both > 0
    ]
    case = 0
    if remainder > 0:
        case |= 1
    if stacks > 0:
        case |= 2
    return cases[case]

class Stage(Item):
    def __init__(self, result, items):
        super().__init__('paper', 1, ItemNbt(ItemDisplay(
                f'Order Form: {result.get_name()}',
                [
                    'Official Order Form',
                    'Required items:'
                ]
            ), [],
            [Enchantments()]
        ))
        self.result = result
        self.items = items
        self.next_stage = None
        self.complete = len(items) == 0
        if server_name:
            self.nbt.display.lore[0][0] += f' of {server_name}'
        if self.complete:
            self.nbt.display.custom_name = 'Completed ' + self.nbt.display.custom_name
            self.nbt.display.lore[1] = ['Complete!']
        for item in self.items:
            self.nbt.display.lore.append([f' - {get_quantity(item.count)}: {item.get_name()}'])
    def next(self):
        next_items = self.items[0:]
        if next_items[0].count > 64:
            next_items[0].count -= 64
        else:
            next_items = next_items[1:]
        if self.next_stage == None:
            self.next_stage = Stage(self.result, next_items)
        return self.next_stage
    def get_trade(self):
        if self.complete:
            return Trade(self, self.result)
        item = self.items[0]
        return Trade(self, self.next(), item.stack(min(item.count, 64)))

class OrderForm(object):
    def __init__(self, price, result, requirements = []):
        self.price = BankNote(price[0], value=price[1])
        self.result = result
        self.requirements = requirements
        self.stages = [Stage(self.result, self.requirements[0:])]
        while not last(self.stages).complete:
            self.stages.append(last(self.stages).next())
    def purchase(self, villager):
        villager.trades.append(Trade(self.price, self.stages[0], Item('paper')))
    def completed(self, villager):
        villager.trades.append(last(self.stages).get_trade())
    def progress(self, villager):
        for stage in self.stages:
            if not stage.complete:
                villager.trades.append(stage.get_trade())
