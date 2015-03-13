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
factory = DocketsBackendFactory(redis_client, wait_time=1)
backend = factory.create_backend_for_group('testing')
instance = Deferrable(backend, redis_client=redis_client)

class EventConsumer(object):
    def __init__(self):
        self.mocks = {}
        for event in ['push', 'pop', 'empty', 'complete', 'expire',
                      'retry', 'error', 'debounce_hit', 'debounce_miss']:
            self.mocks[event] = Mock()

    def reset_mocks(self):
        for mock in self.mocks.itervalues():
            mock.reset_mock()

    def assert_event_emitted(self, event):
        mock = self.mocks[event]
        assert mock.called_once()

    def assert_event_not_emitted(self, event):
        mock = self.mocks[event]
        assert not mock.called

    def __getattribute__(self, attr):
        if attr.startswith('on'):
            mock = self.mocks[attr[3:]]
            fn = lambda item: mock(item)
            return fn
        return super(EventConsumer, self).__getattribute__(attr)

event_consumer = EventConsumer()
instance.register_event_consumer(event_consumer)

my_mock = Mock()
RETRIABLE_ALLOW_FAIL = True

@instance.deferrable
def simple_deferrable(*args, **kwargs):
    my_mock(*args, **kwargs)

@instance.deferrable(error_classes=[ValueError], max_attempts=3)
def retriable_deferrable(should_raise):
    global RETRIABLE_ALLOW_FAIL
    if should_raise and RETRIABLE_ALLOW_FAIL:
        my_mock(should_raise)
        raise ValueError()
    my_mock(should_raise)

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
        global RETRIABLE_ALLOW_FAIL
        RETRIABLE_ALLOW_FAIL = True
        self.item = {'id': str(uuid1())}

    def tearDown(self):
        instance.clear_metadata_producer_consumers()
        event_consumer.reset_mocks()
        backend.queue.flush()
        backend.error_queue.flush()
        my_mock.reset_mock()

    def test_push_item_to_error_queue(self):
        self.assertEqual(0, len(backend.error_queue))

        try:
            1/0
        except:
            instance._push_item_to_error_queue(self.item)

        event_consumer.assert_event_emitted('error')

        self.assertEqual(1, len(backend.error_queue))
        envelope, item = backend.error_queue.pop()
        event_consumer.assert_event_emitted('pop')
        self.assertEqual(item['id'], self.item['id'])
        self.assertEqual(item['error']['error_type'], 'ZeroDivisionError')

    def test_deferrable_decorator(self):
        @instance.deferrable
        def method(*args, **kwargs):
            pass
        self.assertTrue(callable(method.later))

    def test_simple_function(self):
        simple_deferrable.later(1, b=2)
        event_consumer.assert_event_emitted('push')
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        my_mock.assert_called_once_with(1, b=2)

        event_consumer.reset_mocks()
        instance.run_once() # Should do nothing further, queue should be empty
        event_consumer.assert_event_emitted('empty')
        event_consumer.assert_event_not_emitted('pop')
        event_consumer.assert_event_not_emitted('complete')
        my_mock.assert_called_once_with(1, b=2)

    def test_simple_function_with_unicode_args(self):
        simple_deferrable.later(u"d'\xc9vry")
        event_consumer.assert_event_emitted('push')
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        my_mock.assert_called_once_with(u"d'\xc9vry")

    def test_simple_function_callable_normally(self):
        simple_deferrable('bacon')
        event_consumer.assert_event_not_emitted('push')
        my_mock.assert_called_once_with('bacon')

    def test_retriable_with_no_error(self):
        retriable_deferrable.later(False)
        event_consumer.assert_event_emitted('push')
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        my_mock.assert_called_once_with(False)

    def test_retriable_recover(self):
        global RETRIABLE_ALLOW_FAIL

        retriable_deferrable.later(True)
        event_consumer.assert_event_emitted('push')
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('retry')
        self.assertTrue(my_mock.called_once_with(True))

        RETRIABLE_ALLOW_FAIL = False
        event_consumer.reset_mocks()
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_not_emitted('retry')
        event_consumer.assert_event_not_emitted('error')
        event_consumer.assert_event_emitted('complete')
        self.assertTrue(my_mock.has_calls((True,), (False,)))

    def test_retriable_goes_to_error_queue(self):
        retriable_deferrable.later(True)
        instance.run_once()
        instance.run_once()

        event_consumer.reset_mocks()
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('error')
        event_consumer.assert_event_emitted('complete')

        self.assertEqual(0, len(instance.backend.queue))
        self.assertEqual(1, len(instance.backend.error_queue))

    def test_delay(self):
        delayed_deferrable.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        instance.run_once()
        event_consumer.assert_event_not_emitted('pop')
        event_consumer.assert_event_not_emitted('complete')
        self.assertFalse(my_mock.called)

        time.sleep(1.01)
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertTrue(my_mock.called)

    def test_delay_with_debounce(self):
        # This one should get queued immediately with the fast debounce
        debounced_deferrable.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        event_consumer.assert_event_emitted('debounce_miss')
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertEqual(1, len(my_mock.mock_calls))

        # This one gets delayed
        event_consumer.reset_mocks()
        debounced_deferrable.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        event_consumer.assert_event_emitted('debounce_miss')

        # And this one gets debounced and skipped
        event_consumer.reset_mocks()
        debounced_deferrable.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        event_consumer.assert_event_emitted('debounce_hit')
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertEqual(1, len(my_mock.mock_calls))

        event_consumer.reset_mocks()
        time.sleep(1.01)
        instance.run_once()
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertEqual(2, len(my_mock.mock_calls))

    def test_delay_with_debounce_always_delay(self):
        debounced_deferrable_always_delay.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        event_consumer.assert_event_emitted('debounce_miss')

        event_consumer.reset_mocks()
        debounced_deferrable_always_delay.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('debounce_hit')
        instance.run_once()
        event_consumer.assert_event_emitted('empty')
        self.assertEqual(0, len(my_mock.mock_calls))

        event_consumer.reset_mocks()
        time.sleep(1)
        instance.run_once()
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertEqual(1, len(my_mock.mock_calls))

        event_consumer.reset_mocks()
        debounced_deferrable_always_delay.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        time.sleep(1)
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertEqual(2, len(my_mock.mock_calls))

    def test_debounce_does_not_affect_different_args(self):
        debounced_deferrable.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')

        event_consumer.reset_mocks()
        debounced_deferrable.later('hummus', 'flatbread')
        event_consumer.assert_event_emitted('push')

        time.sleep(1)
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')

        event_consumer.reset_mocks()
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertEqual(2, len(my_mock.mock_calls))

    def test_runs_with_ttl(self):
        ttl_deferrable.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        time.sleep(0.5)
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        self.assertTrue(my_mock.called)

    def test_ttl_expiry(self):
        ttl_deferrable.later('beans', 'cornbread')
        event_consumer.assert_event_emitted('push')
        time.sleep(1.5)
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('expire')
        event_consumer.assert_event_emitted('complete')
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
        event_consumer.assert_event_emitted('push')
        instance.run_once()
        event_consumer.assert_event_emitted('pop')
        event_consumer.assert_event_emitted('complete')
        my_mock.assert_called_once_with(1, b=2)
        metadata_mock.assert_called_once_with(metadata_id)

    def test_registering_duplicate_metadata_namespace_raises(self):
        class ExampleMetadataProducerConsumer(MetadataProducerConsumer):
            NAMESPACE = 'testing'
        instance.register_metadata_producer_consumer(ExampleMetadataProducerConsumer())
        with self.assertRaises(ValueError):
            instance.register_metadata_producer_consumer(ExampleMetadataProducerConsumer())
