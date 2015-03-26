from .base import BackendFactory, Backend
from ..queue.sqs import SQSQueue

class SQSBackendFactory(BackendFactory):
    def __init__(self, sqs_connection_thunk, visibility_timeout=30, wait_time=10):
        """To allow backends to be initialized lazily, this factory requires a thunk
        (parameter-less closure) which returns an initialized SQS connection. This thunk
        is called as late as possible to initialize the connection and perform operations
        against the SQS API. We do this so that backends can be made available at import time
        without requiring a connection to be created at import time as well."""

        self.sqs_connection_thunk = sqs_connection_thunk
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time

    def _create_backend_for_group(self, group):
        error_queue = SQSQueue(self.sqs_connection_thunk,
                               self._queue_name('{}_error'.format(group)),
                               self.visibility_timeout,
                               self.wait_time)
        queue = SQSQueue(self.sqs_connection_thunk,
                         self._queue_name(group),
                         self.visibility_timeout,
                         self.wait_time,
                         redrive_queue=error_queue)
        return SQSBackend(group, queue, error_queue)

class SQSBackend(Backend):
    pass
