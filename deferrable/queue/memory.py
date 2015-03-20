from __future__ import absolute_import

import time
import logging
from Queue import Queue as PythonQueue, PriorityQueue, Empty

from .base import Queue

class InMemoryQueue(Queue):
    """InMemoryQueue does not support reclamation of items that
    were popped but never completed. Pop is final and complete is a no-op.

    Really, you probably only want to use this backend for testing."""
    def __init__(self, group, timeout):
        self.group = group
        self.queue = PythonQueue()
        self.delay_queue = PriorityQueue()
        self.timeout = timeout

    def _push_to_delay_queue(self, item, delay_seconds):
        score = time.time() + delay_seconds
        self.delay_queue.put((score, item))

    def _move_from_delay_queue(self):
        now = time.time()
        while True:
            try:
                score, item = self.delay_queue.get(block=False)
                if score < now:
                    self.queue.put(item)
                else:
                    break
            except Empty:
                return
        # If you get to here, you popped something you shouldn't have
        # because it wasn't time for it to go yet
        self.delay_queue.put((score, item))

    def _push(self, item):
        if item.get('delay'):
            self._push_to_delay_queue(item, item['delay'])
        else:
            self.queue.put(item)

    def _push_batch(self, items):
        result = []
        for item in items:
            try:
                self._push(item)
                result.append((item, True))
            except Exception:
                logging.exception("Error pushing item {}".format(item))
                result.append((item, False))
        return result

    def _pop(self):
        self._move_from_delay_queue()
        try:
            result = self.queue.get(block=bool(self.timeout), timeout=self.timeout)
            return result, result
        except Empty:
            return None, None

    def _pop_batch(self, batch_size):
        batch = []
        for _ in range(batch_size):
            envelope, item = self._pop()
            if envelope:
                batch.append((envelope, item))
            else:
                break
        return batch

    def _complete(self, envelope):
        return None

    def _complete_batch(self, envelopes):
        return [(envelope, True) for envelope in envelopes]

    def _flush(self):
        self.queue = PythonQueue()
        self.delay_queue = PriorityQueue()

    def _stats(self):
        return {'available': self.queue.qsize(),
                'in_flight': 0,
                'delayed': self.delay_queue.qsize()}
