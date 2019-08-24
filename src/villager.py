from dataclasses import (dataclass, field)
from typing import Optional

from mcpack import (Function, FunctionTag)

from .items import *


@dataclass
class Trade:
    template = get_pkg_data('villager.json')['templates']['Trade']
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
class Villager:
    template = get_pkg_data('villager.json')['templates']['Villager']
    name: str
    coords: str
    profession: str
    biome: Optional[str] = 'plains'
    trades: Optional[list] = field(default_factory=list)

    def set(self, _pack, root_name, tag_name):
        def get_list(func, _values):
            return ','.join([func(value) for value in _values])
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
        _path = tag_name + '/' + self.name
        _pack.set(_path, Function(self.template.format(*values)), )
        if tag_name not in _pack[root_name].function_tags:
            _pack.set(resolve(tag_name, None, root_name), FunctionTag())
        _pack[root_name].function_tags[tag_name].values.append(resolve(_path, _pack))
