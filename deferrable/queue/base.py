class Queue(object):
    FIFO = True
    SUPPORTS_DELAY = True

    def __init__(self, *args, **kwargs):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()

    def _push(self, item):
        raise NotImplementedError()

    def _pop(self):
        raise NotImplementedError()

    def _complete(self, envelope):
        raise NotImplementedError()

    def _flush(self):
        raise NotImplementedError()

    def push(self, item):
        return self._push(item)

    def pop(self):
        return self._pop()

    def complete(self, envelope):
        return self._complete(envelope)

    def flush(self):
        return self._flush()
