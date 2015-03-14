from .base import BackendFactory, Backend
from ..queue.memory import InMemoryQueue

class InMemoryBackendFactory(BackendFactory):
    def __init__(self, timeout=None):
        self.timeout = timeout

    def _create_backend_for_group(self, group):
        queue_name = self._queue_name(group)
        queue = InMemoryQueue(queue_name, self.timeout)
        error_queue = InMemoryQueue(queue_name, self.timeout)
        return InMemoryBackend(group, queue, error_queue)

class InMemoryBackend(Backend):
    pass
