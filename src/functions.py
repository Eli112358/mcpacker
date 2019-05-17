from mcpack import (Function, FunctionTag)
from mcpacker.items import resolve
from datetime import datetime
import json

colors = [
    "black",
    "dark_blue",
    "dark_green",
    "dark_aqua",
    "dark_red",
    "dark_purple",
    "gold",
    "gray",
    "dark_gray",
    "blue",
    "green",
    "aqua",
    "red",
    "light_purple",
    "yellow"
]

class FunctionWrapper(object):
    def __init__(self, body=""):
        self.function = Function(body)
    def add_text(self, text):
        self.function.body += text
    def add_lines(self, lines):
        self.add_text("\n".join(lines) + ("\n" if len(lines) else ""))
    def add_indexed(self, size, text):
        self.add_lines([text.format(i) for i in range(size)])
    def set(self, pack, path, callback=None):
        if not len(self.function.body): return
        pack[path] = self.function
        if callback: callback()

class Functions(dict):
    def add(self, relpath, body=[""]):
        self[relpath] = FunctionWrapper("\n".join(body))
    def add_data(self, pack):
        data_lines = lambda path, object, entry, i: pack.data["function_templates"][path]["template"].format(*data_format(object, entry, i))
        data_format = lambda object, entry, i: [i]+entry[1:] if "iterator" in object else entry
        data_range = lambda object, entry: entry[0] if "iterator" in object else 1
        data_lines1 = lambda object, path, entry: [data_lines(path, object, entry, i) for i in range(data_range(object, entry))]
        [self[path].add_lines(data_lines1(object, path, entry)) for path,object in pack.data["function_templates"].items() for entry in object["data"]]
    def load(self, pack):
        if not "function_code" in pack.data: return
        [self[path].add_lines(lines) for path,lines in pack.data["function_code"].items()]
    def set(self, pack):
        [func.set(pack, resolve(path, pack)) for path,func in self.items()]

class SelfTaggedFunction(FunctionWrapper):
    def __init__(self, pack, relpath, body="", namespace="minecraft"):
        self.pack = pack
        self.relpath = relpath
        self.namespace = namespace
        self.fullpath = resolve(relpath, pack)
        super().__init__(body)
    def add_to_tag(self, path):
        if not self.relpath in self.pack[self.namespace].function_tags:
            self.create_tag()
        self.pack[self.namespace].function_tags[self.relpath].values.append(path)
    def create_tag(self):
        self.pack[resolve(self.relpath, None, self.namespace)] = FunctionTag()
    def set(self, pack=None, path=None):
        super().set(self.pack, self.fullpath, lambda: self.add_to_tag(self.fullpath))

class Load(SelfTaggedFunction):
    def __init__(self, pack, objectives=[]):
        super().__init__(pack, "load")
        self.add_lines([f"scoreboard objectives add {name}" for name in objectives])

class Tick(SelfTaggedFunction):
    operations = [
        "set @a[scores={{{0}=1..}}] {0} 0",
        "add @a {} 0",
        "enable @a {}"
    ]
    def __init__(self, pack, body = ""):
        super().__init__(pack, "tick", body)
        if "options" in pack.data:
            self.add_lines([pack.data["options"]["pattern"].format(*values) for values in pack.data["options"]["features"]])
    def set(self, pack, path):
        objectives = [] if not "objectives" in pack.data else pack.data["objectives"]
        names = [name.split(" ")[0] for name in objectives if name.split(" ")[1] == "trigger"]
        self.add_lines(["scoreboard players " + op[0:].format(name) for op in self.operations for name in names])
        super().set(pack, path)

class Built(SelfTaggedFunction):
    def __init__(self, pack):
        today = datetime.today()
        tellraw = "tellraw @s " + json.dumps(["",
            {
                "text": today.strftime("%Y-%m-%d"),
                "color": colors[today.timetuple().tm_yday%len(colors)]
            },
            {
                "text": f" | {pack.name}",
                "color": "white"
            }
        ])
        super().__init__(pack, "built", tellraw, "main")
