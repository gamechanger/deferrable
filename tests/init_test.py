from uuid import uuid1
import time

from unittest import TestCase
from mock import Mock
from redis import StrictRedis

from deferrable import Deferrable
from deferrable.metadata import MetadataProducerConsumer
from deferrable.backend.dockets import DocketsBackendFactory

# We need these at module scope so we can create a test method with
# the decorator. These tests should work with any backend that
# passes the standard queue tests. Ideally, we'd want to run these
# with each backend. TODO.
redis_client = StrictRedis()
factory = DocketsBackendFactory(redis_client, wait_time=-1)
backend = factory.create_backend_for_group('testing')
instance = Deferrable(backend, redis_client=redis_client)

my_mock = Mock()

@instance.deferrable
def simple_deferrable(*args, **kwargs):
    my_mock(*args, **kwargs)

@instance.deferrable(delay_seconds=1)
def delayed_deferrable(foo, bar, *args, **kwargs):
    my_mock(foo, bar, *args, **kwargs)

@instance.deferrable(debounce_seconds=1)
def debounced_deferrable(foo, bar, *args, **kwargs):
    my_mock(foo, bar, *args, **kwargs)

@instance.deferrable(debounce_seconds=1, debounce_always_delay=True)
def debounced_deferrable_always_delay(foo, bar, *args, **kwargs):
    my_mock(foo, bar, *args, **kwargs)

@instance.deferrable(ttl_seconds=1)
def ttl_deferrable(*args, **kwargs):
    my_mock(*args, **kwargs)

class TestDeferrable(TestCase):
    def setUp(self):
        self.item = {'id': str(uuid1())}

    def tearDown(self):
        instance.clear_metadata_producer_consumers()
        backend.queue.flush()
        backend.error_queue.flush()
        my_mock.reset_mock()

    def test_push_item_to_error_queue(self):
        self.assertEqual(0, len(backend.error_queue))

        try:
            1/0
        except:
            instance._push_item_to_error_queue(self.item)

        self.assertEqual(1, len(backend.error_queue))
        envelope, item = backend.error_queue.pop()
        self.assertEqual(item['id'], self.item['id'])
        self.assertEqual(item['error']['error_type'], 'ZeroDivisionError')

    def test_deferrable_decorator(self):
        @instance.deferrable
        def method(*args, **kwargs):
            pass
        self.assertTrue(callable(method.later))

    def test_simple_function(self):
        simple_deferrable.later(1, b=2)
        instance.run_once()
        my_mock.assert_called_once_with(1, b=2)
        instance.run_once() # Should do nothing further, queue should be empty
        my_mock.assert_called_once_with(1, b=2)

    def test_simple_function_with_unicode_args(self):
        simple_deferrable.later(u"d'\xc9vry")
        instance.run_once()
        my_mock.assert_called_once_with(u"d'\xc9vry")

    def test_simple_function_callable_normally(self):
        simple_deferrable('bacon')
        my_mock.assert_called_once_with('bacon')

    def test_delay(self):
        delayed_deferrable.later('beans', 'cornbread')
        instance.run_once()
        self.assertFalse(my_mock.called)
        time.sleep(1.01)
        instance.run_once()
        self.assertTrue(my_mock.called)

    def test_delay_with_debounce(self):
        # This one should get queued immediately with the fast debounce
        debounced_deferrable.later('beans', 'cornbread')
        instance.run_once()
        self.assertEqual(1, len(my_mock.mock_calls))

        # This one gets delayed
        debounced_deferrable.later('beans', 'cornbread')
        # And this one gets debounced and skipped
        debounced_deferrable.later('beans', 'cornbread')
        instance.run_once()
        self.assertEqual(1, len(my_mock.mock_calls))
        time.sleep(1.01)
        instance.run_once()
        instance.run_once()
        self.assertEqual(2, len(my_mock.mock_calls))

    def test_delay_with_debounce_always_delay(self):
        debounced_deferrable_always_delay.later('beans', 'cornbread')
        debounced_deferrable_always_delay.later('beans', 'cornbread')
        instance.run_once()
        self.assertEqual(0, len(my_mock.mock_calls))
        time.sleep(1)
        instance.run_once()
        instance.run_once()
        self.assertEqual(1, len(my_mock.mock_calls))
        debounced_deferrable_always_delay.later('beans', 'cornbread')
        time.sleep(1)
        instance.run_once()
        self.assertEqual(2, len(my_mock.mock_calls))

    def test_debounce_does_not_affect_different_args(self):
        debounced_deferrable.later('beans', 'cornbread')
        debounced_deferrable.later('hummus', 'flatbread')
        time.sleep(1)
        instance.run_once()
        instance.run_once()
        self.assertEqual(2, len(my_mock.mock_calls))

    def test_runs_with_ttl(self):
        ttl_deferrable.later('beans', 'cornbread')
        time.sleep(0.5)
        instance.run_once()
        self.assertTrue(my_mock.called)

    def test_ttl_expiry(self):
        ttl_deferrable.later('beans', 'cornbread')
        time.sleep(1.5)
        instance.run_once()
        self.assertFalse(my_mock.called)

    def test_simple_function_with_metadata(self):
        metadata_id = uuid1()
        metadata_mock = Mock()
        class ExampleMetadataProducerConsumer(MetadataProducerConsumer):
            NAMESPACE = 'testing'
            def produce_metadata(self):
                return metadata_id
            def consume_metadata(self, metadata):
                metadata_mock(metadata)

        instance.register_metadata_producer_consumer(ExampleMetadataProducerConsumer())
        simple_deferrable.later(1, b=2)
        instance.run_once()
        my_mock.assert_called_once_with(1, b=2)
        metadata_mock.assert_called_once_with(metadata_id)

    def test_registering_duplicate_metadata_namespace_raises(self):
        class ExampleMetadataProducerConsumer(MetadataProducerConsumer):
            NAMESPACE = 'testing'
        instance.register_metadata_producer_consumer(ExampleMetadataProducerConsumer())
        with self.assertRaises(ValueError):
            instance.register_metadata_producer_consumer(ExampleMetadataProducerConsumer())
