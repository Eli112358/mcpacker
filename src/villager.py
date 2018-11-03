from mcpack import (Function, FunctionTag)
from mcpacker.items import (escape, get_name, resolve)
import copy

class Trade(object):
    def __init__(self, buy, sell, buyB = None, rewardExp = 1, maxUses = 1000, uses = 0):
        self.buy = buy
        self.buyB = buyB
        self.sell = sell
        self.rewardExp = rewardExp
        self.maxUses = maxUses
        self.uses = uses
    def dump(self):
        result = f'{{buy:{self.buy.trade()},'
        if self.buyB:
            result += f'buyB:{self.buyB.trade()},'
        result += f'sell:{self.sell.trade()},'
        result += f'rewardExp:{self.rewardExp}b,'
        result += f'maxUses:{self.maxUses},'
        result += f'uses:{self.uses}}}'
        return result

class Villager(object):
    def __init__(self, name, coords, profession, trades = []):
        self.name = name
        self.escaped_name = escape(f'"{get_name(name)}"')
        self.coords = coords
        self.profession = profession
        self.trades = copy.deepcopy(trades)
    def set(self, pack, root_name):
        trade_dump = []
        for trade in self.trades:
            trade_dump.append(trade.dump())
        body = f'summon villager {self.coords} {{'
        body += f'CustomName:"{self.escaped_name}",'
        body += f'Profession:{self.profession},'
        body += 'CareerLevel:64,Tags:["shop","villager"],'
        body += 'Invulnerable:1,NoGravity:1,Silent:1,'
        body += 'NoAI:1,DeathLootTable:"empty",CanPickUpLoot:0,'
        body += 'Offers:{Recipes:['
        body += ','.join(trade_dump)
        body += ']}}\n'
        pack[f'{pack.name}:villagers/{self.name}'] = Function(body)
        if not 'villagers' in pack[root_name].function_tags:
            pack[resolve('villagers', None, root_name)] = FunctionTag([])
        pack[root_name].function_tags['villagers'].values.append(resolve(f'villagers/{self.name}', pack))
