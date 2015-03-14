class Queue(object):
    FIFO = True
    SUPPORTS_DELAY = True

    def __init__(self, *args, **kwargs):
        raise NotImplementedError()

    def _push(self, item):
        raise NotImplementedError()

    def _pop(self):
        raise NotImplementedError()

    def _complete(self, envelope):
        raise NotImplementedError()

    def _flush(self):
        raise NotImplementedError()

    def _stats(self):
        """Should return a dictionary with as many of the following
        stat keys as the queue can report on:

        - available
        - in_flight
        - delayed
        """
        raise NotImplementedError()

    def push(self, item):
        return self._push(item)

    def pop(self):
        return self._pop()

    def complete(self, envelope):
        return self._complete(envelope)

    def flush(self):
        return self._flush()

    def stats(self):
        return self._stats()
