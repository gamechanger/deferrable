from unittest import TestCase

from boto.sqs.connection import SQSConnection

from deferrable.backend.sqs import SQSBackendFactory, SQSBackend
from deferrable.queue.sqs import SQSQueue

class TestSQSBackendFactory(TestCase):
    def setUp(self):
        self.sqs_connection = SQSConnection()
        self.factory = SQSBackendFactory(self.sqs_connection)

    def test_create_backend_for_group(self):
        for group in ['testing']:
            backend = self.factory.create_backend_for_group(group)
            self.assertIsInstance(backend, SQSBackend)
            self.assertIsInstance(backend.queue, SQSQueue)
            self.assertIsInstance(backend.error_queue, SQSQueue)

class TestSQSBackend(TestCase):
    pass
