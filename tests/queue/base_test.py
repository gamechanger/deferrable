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
        self.test_item_1 = {'id': str(uuid1()), 'error': {'id': str(uuid1())}}
        self.test_item_2 = {'id': str(uuid1()), 'error': {'id': str(uuid1())}}
        self.test_item_delay = {'id': str(uuid1()), 'error': {'id': str(uuid1())}, 'delay': 1}

    def tearDown(self):
        self._flush_all_queues()

    def _flush_all_queues(self):
        for queue in self.all_queues(verbose=False):
            if hasattr(queue, '_slow_flush'):
                queue._slow_flush()
            else:
                queue.flush()

    def all_queues(self, verbose=True):
        redis_client = StrictRedis(db=15)
        factory = DocketsBackendFactory(redis_client, wait_time=0)
        backend = factory.create_backend_for_group('testing')
        if verbose:
            print "Testing Dockets Queue..."
        yield backend.queue
        if verbose:
            print "Testing Dockets Error Queue..."
        yield backend.error_queue

        backend = InMemoryBackendFactory().create_backend_for_group('testing')
        if verbose:
            print "Testing Memory Queue..."
        yield backend.queue

        fake_sqs = mock_sqs()
        fake_sqs.start()
        factory = SQSBackendFactory(lambda: SQSConnection(), wait_time=None)
        backend = factory.create_backend_for_group('testing')
        if verbose:
            print "Testing SQS Queue with lazy connection thunk..."
        yield backend.queue
        fake_sqs.stop()

    def test_len_with_no_items(self):
        for queue in self.all_queues():
            self.assertEquals(0, queue.stats()['available'])

    def test_push_increments_len(self):
        for queue in self.all_queues():
            queue.push(self.test_item_1)
            self.assertEquals(1, queue.stats()['available'])
            queue.push(self.test_item_2)
            self.assertEquals(2, queue.stats()['available'])

    def test_push_pop_complete(self):
        for queue in self.all_queues():
            queue.push(self.test_item_1)
            envelope, item = queue.pop()
            self.assertEqual(item, self.test_item_1)
            queue.complete(envelope)
            self.assertEqual(0, queue.stats()['available'])

    def test_push_pop_batch(self):
        for queue in self.all_queues():
            queue.push_batch([self.test_item_1, self.test_item_2])
            self.assertEqual(2, queue.stats()['available'])
            batch = queue.pop_batch(2)
            self.assertItemsEqual(map(lambda x: x[1], batch), [self.test_item_1, self.test_item_2])

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

    def test_pop_batch(self):
        for queue in self.all_queues():
            queue.push(self.test_item_1)
            queue.push(self.test_item_2)
            self.assertEquals(2, queue.stats()['available'])
            batch = queue.pop_batch(2)
            self.assertEqual(2, len(batch))
            if queue.FIFO:
                self.assertEqual(self.test_item_1, batch[0][1])
                self.assertEqual(self.test_item_2, batch[1][1])

    def test_push_with_delay(self):
        for queue in self.all_queues():
            if not queue.SUPPORTS_DELAY:
                logging.warn('Skipping test for non-delayable queue {}'.format(queue))
                continue
            queue.push(self.test_item_delay)
            self.assertEqual(0, queue.stats()['available'])

            envelope, item = queue.pop()
            self.assertIsNone(envelope)
            self.assertIsNone(item)
            self.assertEqual(0, queue.stats()['available'])
            time.sleep(1.01)

            envelope, item = queue.pop()
            self.assertIsNotNone(envelope)
            self.assertIsNotNone(item)
            self.assertEqual(0, queue.stats()['available'])

    def test_complete_batch(self):
        for queue in self.all_queues():
            queue.push(self.test_item_1)
            queue.push(self.test_item_2)
            envelope_1, item_1 = queue.pop()
            envelope_2, item_2 = queue.pop()
            # hack for Dockets error queue
            if envelope_1 == envelope_2:
                envelope_1 = self.test_item_1
                envelope_2 = self.test_item_2
            result = queue.complete_batch([envelope_1, envelope_2])
            self.assertEqual(0, queue.stats()['available'])
            self.assertEqual(0, queue.stats().get('in_flight', 0))
            self.assertEqual(result, [(envelope_1, True), (envelope_2, True)])

    def test_touch(self):
        """Don't see a great way to test this one, let's just make sure
        we can call the function for now."""
        for queue in self.all_queues():
            queue.push(self.test_item_1)
            envelope, item = queue.pop()
            queue.touch(envelope, 30)
