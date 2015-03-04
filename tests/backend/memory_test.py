from unittest import TestCase
from mock import Mock

from deferrable.backend.memory import InMemoryBackendFactory, InMemoryBackend
from deferrable.queue.memory import InMemoryQueue, InMemoryErrorQueue

class TestDocketsBackendFactory(TestCase):
    def setUp(self):
        self.factory = InMemoryBackendFactory()

    def test_create_backend_for_group(self):
        for group in [None, 'testing']:
            backend = self.factory.create_backend_for_group(group)
            self.assertIsInstance(backend, InMemoryBackend)
            self.assertIsInstance(backend.queue, InMemoryQueue)
            self.assertIsInstance(backend.error_queue, InMemoryErrorQueue)

class TestDocketsBackend(TestCase):
    pass
