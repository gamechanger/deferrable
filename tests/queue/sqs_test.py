from unittest import TestCase
from uuid import uuid1
import time
from contextlib import contextmanager

from boto.sqs.connection import SQSConnection

from deferrable.backend.sqs import SQSBackendFactory
from deferrable.queue.sqs import SQSQueue

def test_function():
    # pass this in to test pickling in and out of SQS
    pass

class TestSQSQueue(TestCase):
    """SQS is really finicky since it's eventually consistent. Our
    standard queue tests don't behave nicely with it, so we needed
    to implement its own test suite."""
    @classmethod
    def setUpClass(cls):
        cls.sqs_connection = SQSConnection()
        cls.factory = SQSBackendFactory(cls.sqs_connection, visibility_timeout=1, wait_time=None)
        cls.backend = cls.factory.create_backend_for_group('testing')
        cls.queue = cls.backend.queue
        cls.queue._slow_flush()

    def setUp(self):
        self.test_item_1 = {'id': str(uuid1()), 'fn': test_function}
        self.test_item_2 = {'id': str(uuid1()), 'fn': test_function}
        self.test_item_delay = {'id': str(uuid1()), 'fn': test_function, 'delay': 3}

    def tearDown(self):
        self.queue._slow_flush()

    def pop_until_not_empty(self):
        attempt = 1
        while attempt <= 5:
            envelope, item = self.queue.pop()
            if envelope:
                return envelope, item
            attempt += 1
        raise ValueError('could not read anything from the queue')

    def test_push_pop_complete(self):
        self.queue.push(self.test_item_1)
        envelope, item = self.pop_until_not_empty()
        self.assertEqual(item, self.test_item_1)
        self.queue.complete(envelope)

    def test_push_with_delay(self):
        self.queue.push(self.test_item_delay)
        time.sleep(2)
        envelope, item = self.queue.pop()
        self.assertIsNone(envelope)

        time.sleep(1)
        envelope, item = self.pop_until_not_empty()
        self.assertEqual(item, self.test_item_delay)
        self.queue.complete(envelope)
