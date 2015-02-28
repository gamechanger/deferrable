from unittest import TestCase
from redis import StrictRedis

from deferrable.backend.dockets import DocketsBackendFactory
from deferrable.queue.dockets import DocketsQueue, DocketsErrorQueue

class TestDocketsQueue(TestCase):
    def setUp(self):
        self.redis_client = StrictRedis()
        self.factory = DocketsBackendFactory(self.redis_client)
        self.backend = self.factory.create_backend_for_group('test')
        self.queue = self.backend.queue

    def test_make_error_queue(self):
        error_queue = self.queue.make_error_queue()
        self.assertIsInstance(error_queue, DocketsErrorQueue)

class TestDocketsErrorQueue(TestCase):
    pass
