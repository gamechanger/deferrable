from __future__ import absolute_import

import dockets.queue

from . import BackendFactory
from ..queue.dockets import DocketsQueue

class DocketsBackendFactory(BackendFactory):
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def create_backend_for_group(self, group):
        queue = DocketsQueue(self.redis_client, self._queue_name('later', group))
        error_queue = queue.make_error_queue()
        return DocketsBackend(queue, error_queue)

    @staticmethod
    def _queue_name(base, group):
        if group:
            return '{}:{}'.format(base, group)
        return base

class DocketsBackend(Backend):
    pass
