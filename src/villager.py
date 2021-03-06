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
            quote(Namespaced(self.profession)),
            quote(Namespaced(self.biome)),
            get_list(lambda v: quote(v), ['shop', 'villager']),
            get_list(lambda v: v+':1', ['Invulnerable', 'Silent', 'NoAI']),
            quote(Namespaced('empty')),
            get_list(lambda v: v.dump(), self.trades)
        ]
        tag_ns_id = Namespaced(tag_name, root_name)
        _path = tag_ns_id / self.name
        _pack[_path] = Function(self.template.format(*values))
        if tag_name not in _pack[tag_ns_id.type_only('function_tags')]:
            _pack[tag_ns_id] = FunctionTag()
        _pack[tag_ns_id.typed('function_tags')].values.append(_path)
