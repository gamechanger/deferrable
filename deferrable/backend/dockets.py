from __future__ import absolute_import

import dockets.queue

from .base import BackendFactory, Backend
from ..queue.dockets import DocketsQueue

class DocketsBackendFactory(BackendFactory):
    def __init__(self, redis_client, wait_time=3, timeout=300):
        self.redis_client = redis_client
        self.wait_time = wait_time
        self.timeout = timeout

    def _create_backend_for_group(self, group):
        queue = DocketsQueue(self.redis_client,
                             self._queue_name(group),
                             self.wait_time,
                             self.timeout)
        error_queue = queue.make_error_queue()
        return DocketsBackend(group, queue, error_queue)

class DocketsBackend(Backend):
    pass
