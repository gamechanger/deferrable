from .base import BackendFactory, Backend
from ..queue.sqs import SQSQueue

class SQSBackendFactory(BackendFactory):
    def __init__(self, sqs_connection, visibility_timeout=30, wait_time=10):
        self.sqs_connection = sqs_connection
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time

    def create_backend_for_group(self, group):
        queue = SQSQueue(self.sqs_connection,
                         self._queue_name(group),
                         self.visibility_timeout,
                         self.wait_time)
        error_queue = SQSQueue(self.sqs_connection,
                               self._queue_name('{}_error'.format(group)),
                               self.visibility_timeout,
                               self.wait_time)
        return SQSBackend(group, queue, error_queue)

class SQSBackend(Backend):
    pass
