from .base import BackendFactory, Backend
from ..queue.sqs import SQSQueue

class SQSBackendFactory(BackendFactory):
    def __init__(self, sqs_connection_or_thunk, visibility_timeout=30, wait_time=10, create_if_missing=False):
        if callable(sqs_connection_or_thunk):
            self.sqs_connection_thunk = sqs_connection_or_thunk
        else:
            self.sqs_connection_thunk = lambda: sqs_connection_or_thunk
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time
        self.create_if_missing = create_if_missing

    def _create_backend_for_group(self, group):
        queue = SQSQueue(self.sqs_connection_thunk,
                         self._queue_name(group),
                         self.visibility_timeout,
                         self.wait_time,
                         create_if_missing=self.create_if_missing)
        error_queue = SQSQueue(self.sqs_connection_thunk,
                               self._queue_name('{}_error'.format(group)),
                               self.visibility_timeout,
                               self.wait_time,
                               create_if_missing=self.create_if_missing)
        return SQSBackend(group, queue, error_queue)

class SQSBackend(Backend):
    pass
