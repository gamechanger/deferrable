from unittest import TestCase
from uuid import uuid1
from mock import Mock

from deferrable.metadata import MetadataProducerConsumer
from deferrable.pickling import load, dump

class TestMetadataProducerConsumer(TestCase):
    def setUp(self):
        self.item = {'id': uuid1(), 'metadata': {'premade': dump(10)}}
        self.cls = MetadataProducerConsumer
        self.cls.NAMESPACE = 'namespace'
        self.my_mock = Mock()

    def test_raises_on_empty_namespace(self):
        with self.assertRaises(ValueError):
            self.cls.NAMESPACE = None
            self.cls()

    def test_does_not_raise_with_valid_namespace(self):
        self.cls.NAMESPACE = 'namespace'
        self.cls()

    def test_apply_metadata_to_item(self):
        self.cls.produce_metadata = lambda self: 1
        self.cls()._apply_metadata_to_item(self.item)
        self.assertEqual(self.item['metadata']['namespace'], dump(1))

    def test_consume_metadata_from_item(self):
        self.cls.NAMESPACE = 'premade'
        self.cls.consume_metadata = lambda instance, metadata: self.my_mock(metadata)
        self.cls()._consume_metadata_from_item(self.item)
        self.assertTrue(self.my_mock.called_once_with_args(10))
