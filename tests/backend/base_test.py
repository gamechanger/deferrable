from unittest import TestCase

from deferrable.backend.base import BackendFactory

class TestBackendFactory(TestCase):
    def test_queue_name_with_None(self):
        self.assertEqual('deferrable', BackendFactory._queue_name(None))

    def test_queue_name_with_group(self):
        self.assertEqual('deferrable:test', BackendFactory._queue_name('test'))

class TestBackend(TestCase):
    pass
