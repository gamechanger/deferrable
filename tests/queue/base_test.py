"""Tests for basic queue behavior (push, pop, complete) across all
queue implementations."""

import logging
import time

from unittest import TestCase
from redis import StrictRedis
from uuid import uuid1
from moto import mock_sqs
from boto.sqs.connection import SQSConnection

from deferrable.backend.dockets import DocketsBackendFactory
from deferrable.backend.memory import InMemoryBackendFactory
from deferrable.backend.sqs import SQSBackendFactory

class TestAllQueueImplementations(TestCase):
    def setUp(self):
        self._flush_all_queues()
        self.test_item_1 = {'id': str(uuid1())}
        self.test_item_2 = {'id': str(uuid1())}
        self.test_item_delay = {'id': str(uuid1()), 'delay': 1}

    def tearDown(self):
        self._flush_all_queues()

    def _flush_all_queues(self):
        for queue in self.all_queues():
            if hasattr(queue, '_slow_flush'):
                queue._slow_flush()
            else:
                queue.flush()

    def all_queues(self):
        redis_client = StrictRedis(db=15)
        factory = DocketsBackendFactory(redis_client, wait_time=1)
        backend = factory.create_backend_for_group('testing')
        yield backend.queue
        yield backend.error_queue

        backend = InMemoryBackendFactory().create_backend_for_group('testing')
        yield backend.queue

        fake_sqs = mock_sqs()
        fake_sqs.start()
        factory = SQSBackendFactory(SQSConnection(), wait_time=None, create_if_missing=True)
        backend = factory.create_backend_for_group('testing')
        yield backend.queue
        fake_sqs.stop()

    def test_len_with_no_items(self):
        for queue in self.all_queues():
            self.assertEquals(0, len(queue))

    def test_push_increments_len(self):
        for queue in self.all_queues():
            queue.push(self.test_item_1)
            self.assertEquals(1, len(queue))
            queue.push(self.test_item_2)
            self.assertEquals(2, len(queue))

    def test_push_pop_complete(self):
        for queue in self.all_queues():
            queue.push(self.test_item_1)
            envelope, item = queue.pop()
            self.assertEqual(item, self.test_item_1)
            queue.complete(envelope)
            self.assertEqual(0, len(queue))

    def test_pop_is_fifo_with_completes(self):
        for queue in self.all_queues():
            if not queue.FIFO:
                logging.warn('Skipping test for non-FIFO queue {}'.format(queue))
                continue
            queue.push(self.test_item_1)
            queue.push(self.test_item_2)
            envelope, item = queue.pop()
            self.assertEqual(item, self.test_item_1)
            queue.complete(envelope)
            envelope, item = queue.pop()
            self.assertEqual(item, self.test_item_2)
            queue.complete(envelope)

    def test_push_with_delay(self):
        for queue in self.all_queues():
            if not queue.SUPPORTS_DELAY:
                logging.warn('Skipping test for non-delayable queue {}'.format(queue))
                continue
            queue.push(self.test_item_delay)
            self.assertEqual(0, len(queue))

            envelope, item = queue.pop()
            self.assertIsNone(envelope)
            self.assertIsNone(item)
            self.assertEqual(0, len(queue))
            time.sleep(1.01)

            envelope, item = queue.pop()
            self.assertIsNotNone(envelope)
            self.assertIsNotNone(item)
            self.assertEqual(0, len(queue))
