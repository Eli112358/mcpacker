from .items import *
from .villager import Trade


def get_quantity(item):
    _max = get_max_stack(item.id)
    if _max is 1:
        return str(item.count)
    remainder = int(item.count % _max)
    stacks = int((item.count - remainder) / _max)
    cases = [
        '',                              # both == 0
        f'{remainder}',                  # remainder > 0
        f'{stacks}x{_max}',              # stacks > 0
        f'{stacks}x{_max} +{remainder}'  # both > 0
    ]
    return cases[((stacks > 0) << 1) | (remainder > 0)]


class Stage(Item):
    def __init__(self, result, items):
        nbt = Compound(dict(display=dict(
            Name=custom_name('Order Form: ' + result.get_name()),
            Lore=List[String]([
                'Official Order Form',
                'Required items:'
            ])
        )))
        set_enchantments(nbt)
        super().__init__('paper', 1, nbt)
        self.result = result
        self.items = items
        self.next_stage = None
        self.complete = len(items) == 0
        if server_name:
            self.nbt['display']['Lore'][0][0] += f' of {server_name}'
        if self.complete:
            self.nbt['display']['Name'] = custom_name('Completed ' + self.get_name())
            self.nbt['display']['Lore'][1] = 'Complete!'
        for item in self.items:
            self.nbt['display']['Lore'].append(f' - {get_quantity(item)}: {item.get_name()}')

    def next(self):
        next_items = self.items[0:]
        if next_items[0].count > next_items[0].stack(fixed=False):
            next_items[0].count -= next_items[0].stack(fixed=False)
        else:
            next_items = next_items[1:]
        if self.next_stage is None:
            self.next_stage = Stage(self.result, next_items)
        return self.next_stage

    def get_trade(self):
        if self.complete:
            return Trade(self, self.result)
        item = self.items[0]
        return Trade(self, self.next(), item.stack(item.count))


class OrderForm:
    def __init__(self, price, result, requirements=None):
        if requirements is None:
            requirements = []
        self.price = BankNote.parse(price)[0]
        self.result = result
        self.requirements = requirements
        self.stages = [Stage(self.result, self.requirements[0:])]
        while not self.stages[-1].complete:
            self.stages.append(self.stages[-1].next())

    def completed(self, villager):
        villager.trades.append(self.stages[-1].get_trade())

    def progress(self, villager):
        for stage in self.stages:
            if not stage.complete:
                villager.trades.append(stage.get_trade())

    def purchase(self, villager):
        villager.trades.append(Trade(self.price, self.stages[0], Item('paper')))
