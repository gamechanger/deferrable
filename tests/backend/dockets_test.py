from unittest import TestCase
from mock import Mock
from redis import StrictRedis

from deferrable.backend.dockets import DocketsBackendFactory, DocketsBackend
from deferrable.queue.dockets import DocketsQueue, DocketsErrorQueue

class TestDocketsBackendFactory(TestCase):
    def setUp(self):
        self.redis_client = StrictRedis()
        self.factory = DocketsBackendFactory(self.redis_client)

    def test_create_backend_for_group(self):
        for group in [None, 'testing']:
            backend = self.factory.create_backend_for_group(group)
            self.assertIsInstance(backend, DocketsBackend)
            self.assertIsInstance(backend.queue, DocketsQueue)
            self.assertIsInstance(backend.error_queue, DocketsErrorQueue)

    def test_queue_name(self):
        self.assertEqual(self.factory._queue_name('later', None), 'later')
        self.assertEqual(self.factory._queue_name('later', 'testing'), 'later:testing')

class TestDocketsBackend(TestCase):
    pass
