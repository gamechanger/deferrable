class Queue(object):
    def __len__(self):
        raise NotImplementedError()

    def push(self, item):
        return self._push(item)

    def pop(self):
        return self._pop()

    def complete(self, envelope):
        return self._complete(envelope)
