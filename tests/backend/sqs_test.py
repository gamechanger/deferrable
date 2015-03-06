from unittest import TestCase

from boto.sqs.connection import SQSConnection
from moto import mock_sqs

from deferrable.backend.sqs import SQSBackendFactory, SQSBackend
from deferrable.queue.sqs import SQSQueue

class TestSQSBackendFactory(TestCase):
    def setUp(self):
        self.fake_sqs = mock_sqs()
        self.fake_sqs.start()
        self.sqs_connection = SQSConnection()
        self.factory = SQSBackendFactory(self.sqs_connection, create_if_missing=True)

    def tearDown(self):
        self.fake_sqs.stop()

    def test_create_backend_for_group(self):
        for group in ['testing']:
            backend = self.factory.create_backend_for_group(group)
            self.assertIsInstance(backend, SQSBackend)
            self.assertIsInstance(backend.queue, SQSQueue)
            self.assertIsInstance(backend.error_queue, SQSQueue)

class TestSQSBackend(TestCase):
    pass
