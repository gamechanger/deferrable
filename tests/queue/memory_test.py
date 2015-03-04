from unittest import TestCase
import time

from deferrable.backend.memory import InMemoryBackendFactory
from deferrable.queue.memory import InMemoryQueue, InMemoryErrorQueue

class TestInMemoryQueue(TestCase):
    def setUp(self):
        self.factory = InMemoryBackendFactory()
        self.backend = self.factory.create_backend_for_group('test')
        self.queue = self.backend.queue
        self.main_queue = self.queue.queue
        self.delay_queue = self.queue.delay_queue

    def test_push_to_delay_queue(self):
        self.queue._push_to_delay_queue(1, 1)
        self.assertEqual(1, self.delay_queue.qsize())
        self.assertEqual(0, self.main_queue.qsize())

    def test_move_from_delay_queue(self):
        self.queue._push_to_delay_queue(1, 0.1)
        self.queue._move_from_delay_queue()
        self.assertEqual(1, self.delay_queue.qsize())
        self.assertEqual(0, self.main_queue.qsize())

        time.sleep(0.11)
        self.queue._move_from_delay_queue()
        self.assertEqual(0, self.delay_queue.qsize())
        self.assertEqual(1, self.main_queue.qsize())

class TestInMemoryErrorQueue(TestCase):
    pass
