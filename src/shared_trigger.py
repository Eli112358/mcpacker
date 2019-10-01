from mcpack import FunctionTag

from .namespaced import Namespaced


class SharedTrigger:
    namespace = 'trigger'

    def __init__(self, pack, name, source='', skip_objectives=False):
        self.name = name
        self.pack = pack
        self.source = source if source else self.pack.name
        self.skip_objectives = skip_objectives
        self.function = Namespaced(SharedTrigger.namespace, self.source) / self.name
        self.tag = Namespaced(self.name, SharedTrigger.namespace)
        if self.pack.name == self.source:
            parts = [SharedTrigger.namespace, self.name]
            body = ' '.join(parts)
            self.pack.get_data('functions').append(self.function.str)
            self.pack.get_data('function_code').setdefault(self.function.str, [body])
            self.pack.get_data('function_tags').append(str(self.tag))
            if not self.skip_objectives:
                self.pack.get_data('objectives').append(' '.join(reversed(parts)))

    def run_tag(self):
        return 'function #' + str(self.tag)

    def set(self):
        if self.pack.name == self.source:
            self.pack[self.tag] = FunctionTag([self.function], True)
