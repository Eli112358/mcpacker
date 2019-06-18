from mcpack import (Function, FunctionTag)
from typing import Optional
from dataclasses import (dataclass, field)
import copy

from .items import *

@dataclass
class Trade():
    template = '{{buy:{{{}}},{}sell:{{{}}},rewardExp:{},maxUses:{},uses:{},xp:{},priceMultiplier:{},specialPrice:{},demand:{}}}'

    buy: Item
    sell: Item
    buyB: Optional[Item] = None
    rewardExp: Optional[int] = 1
    maxUses: Optional[int] = 1000
    uses: Optional[int] = 0
    xp: Optional[int] = 0
    priceMultiplier: Optional[float] = 1.0
    specialPrice: Optional[int] = 0
    demand: Optional[int] = 0
    def dump(self):
        values = [
            self.buy.trade(),
            f'buyB:{{{self.buyB.trade()}}},' if self.buyB else '',
            self.sell.trade(),
            self.rewardExp,
            self.maxUses,
            self.uses,
            self.xp,
            self.priceMultiplier,
            self.specialPrice,
            self.demand
        ]
        return self.template.format(*values)

@dataclass
class Villager():
    template = 'summon villager {} {{CustomName:{},VillagerData:{{level:8,profession:{},type:{}}},Tags:[{}],{},DeathLootTable:{},CanPickUpLoot:0,Offers:{{Recipes:[{}]}}}}'

    name: str
    coords: str
    profession: str
    biome: Optional[str] = 'plains'
    trades: Optional[list] = field(default_factory=list)
    def set(self, pack, root_name, tag_name):
        get_list = lambda func,values: ','.join([func(value) for value in values])
        values = [
            self.coords,
            quote(escape(quote(get_name(self.name)))),
            quote(resolve(self.profession)),
            quote(resolve(self.biome)),
            get_list(lambda v: quote(v), ['shop', 'villager']),
            get_list(lambda v: v+':1', ['Invulnerable', 'NoGravity', 'Silent', 'NoAI']),
            quote(resolve('empty')),
            get_list(lambda v: v.dump(), self.trades)
        ]
        path = tag_name+'/'+self.name
        pack.set(path, Function(self.template.format(*values)))
        if not tag_name in pack[root_name].function_tags:
            pack.set(resolve(tag_name, None, root_name), FunctionTag())
        pack[root_name].function_tags[tag_name].values.append(resolve(path, pack))
