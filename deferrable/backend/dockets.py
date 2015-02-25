from __future__ import absolute_import

import dockets.queue

from . import Backend, BackedQueue
from ..queue import DeferrableQueue

class DocketsBackend(Backend):
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def for_group(self, group):
        backed_queue = DocketsBackedQueue(dockets.queue.Queue(self.redis_client,
                                                              self._queue_name('later', group),
                                                              use_error_queue=True,
                                                              wait_time=3,
                                                              timeout=300))
        return DeferrableQueue(backed_queue, self.redis_client)

    @staticmethod
    def _queue_name(base, group):
        if group:
            return '{}:{}'.format(base, group)
        return base

class DocketsBackedQueue(BackedQueue):
    def _push(self, item, error_classes=None, attempts=None, max_attempts=None, delay=None):
        self.queue.push(item, error_classes=error_classes,
                        attempts=attempts, max_attempts=max_attempts,
                        delay=delay)

    def _pop(self):
        envelope = self.queue.pop()
        if envelope:
            return envelope.get('item')

    def _complete(self, item):
        self.queue.complete(None) # goddammit
