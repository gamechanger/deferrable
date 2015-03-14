import sys

class Queue(object):
    FIFO = True
    SUPPORTS_DELAY = True
    MAX_POP_BATCH_SIZE = sys.maxint

    def __init__(self, *args, **kwargs):
        raise NotImplementedError()

    def _push(self, item):
        raise NotImplementedError()

    def _pop(self):
        raise NotImplementedError()

    def _pop_batch(self, batch_size):
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

    def pop_batch(self, batch_size):
        if batch_size > self.MAX_POP_BATCH_SIZE:
            raise ValueError("Batch size cannot exceed {}.".format(self.MAX_POP_BATCH_SIZE))
        return self._pop_batch(batch_size)

    def complete(self, envelope):
        return self._complete(envelope)

    def flush(self):
        return self._flush()

    def stats(self):
        return self._stats()
