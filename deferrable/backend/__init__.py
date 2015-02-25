class Backend(object):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError()

    def for_group(self, group):
        raise NotImplementedError()

    def with_registrar(self, registrar):
        self.registrar = registrar
        return self

class BackedQueue(object):
    def __init__(self, queue, *args, **kwargs):
        self.queue = queue

    # Public methods
    def push(self, item, error_classes=None, attempts=None, max_attempts=None, delay=None):
        return self._push(item)

    def pop(self):
        return self._pop()

    def complete(self, item):
        return self._complete(item)

    def stats(self):
        return self._stats()

    # Private methods, implement these in your subclass
    def _push(self, item, error_classes=None, attempts=None, max_attempts=None, delay=None):
        raise NotImplementedError()

    def _pop(self):
        raise NotImplementedError()

    def _complete(self, item):
        raise NotImplementedError()

    def _stats(self):
        pass
