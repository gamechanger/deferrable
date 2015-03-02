import sys
import time
import logging
from uuid import uuid1
import socket
from traceback import format_exc

from .pickling import loads, dumps, build_later_item, unpickle_method_call, pretty_unpickle
from .debounce import get_debounce_strategy, set_last_push_time, set_debounce_key, DebounceStrategy
from .ttl import add_ttl_metadata_to_item, item_is_expired

class Deferrable(object):
    """
    The following events are emitted by Deferrable and may be consumed by
    registering event handlers with the appropriate `on_{event}` methods,
    each of which takes the queue item as its sole argument. Event handlers
    regarding queue operations (e.g. pop) are called *after* the operation
    has taken place.

    - on_push          : item pushed to the non-error queue
    - on_pop           : pop was attempted and returned an item
    - on_empty         : pop was attempted but did not return an item
    - on_complete      : item completed in the non-error queue
    - on_expire        : TTL expiration
    - on_retry         : item execution errored but will be retried
    - on_error         : item execution errored and was pushed to the error queue
    - on_debounce_hit  : item was not queued subject to debounce constraints
    - on_debounce_miss : item is configured for debounce but was queued
    """

    def __init__(self, backend, redis_client=None):
        self.backend = backend
        self.redis_client = redis_client

        self._metadata_producer_consumers = []
        self._event_consumers = []

    def deferrable(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            method = args[0]
            return self._deferrable(method)
        return lambda method: self._deferrable(method, *args, **kwargs)

    def run_once(self):
        envelope, item = self.backend.queue.pop()
        if not envelope:
            self._emit('empty', item)
            return
        self._emit('pop', item)
        item_error_classes = loads(item['error_classes']) or tuple()

        for producer_consumer in self._metadata_producer_consumers:
            producer_consumer._consume_metadata_from_item(item)

        try:
            if item_is_expired(item):
                logging.warn("Deferrable job dropped with expired TTL: {}".format(pretty_unpickle(item)))
                self._emit('expire', item)
                self.backend.queue.complete(envelope)
                self._emit('complete', item)
                return
            method, args, kwargs = unpickle_method_call(item)
            method(*args, **kwargs)
        except tuple(item_error_classes):
            attempts, max_attempts = item['attempts'], item['max_attempts']
            if attempts >= max_attempts - 1:
                self._push_item_to_error_queue(item)
            else:
                item['attempts'] += 1
                self.backend.queue.push(item)
                self._emit('retry', item)
        except Exception:
            self._push_item_to_error_queue(item)

        self.backend.queue.complete(envelope)
        self._emit('complete', item)

    def register_metadata_producer_consumer(self, producer_consumer):
        for existing in self._metadata_producer_consumers:
            if existing.NAMESPACE == producer_consumer.NAMESPACE:
                raise ValueError('NAMESPACE {} is already in use'.format(producer_consumer.NAMESPACE))
        self._metadata_producer_consumers.append(producer_consumer)

    def clear_metadata_producer_consumers(self):
        self._metadata_producer_consumers = []

    def register_event_consumer(self, event_consumer):
        self._event_consumers.append(event_consumer)

    def clear_event_consumers(self):
        self._event_consumers = []

    def _emit(self, event, item):
        handler_name = 'on_{}'.format(event)
        for event_consumer in self._event_consumers:
            if hasattr(event_consumer, handler_name):
                getattr(event_consumer, handler_name)(item)

    def _push_item_to_error_queue(self, item):
        """Put information about the current exception into the item's `error`
        key and push the transformed item to the error queue."""
        exc_info = sys.exc_info()
        assert exc_info[0], "_push_error_item must be called from inside an exception handler"
        error_info = {
            'error_type': str(exc_info[0].__name__),
            'error_text': str(exc_info[1]),
            'traceback': format_exc(),
            'hostname': socket.gethostname(),
            'ts': time.time(),
            'id': str(uuid1())
        }
        item['error'] = error_info
        self.backend.error_queue.push(item)
        self._emit('error', item)

    def _validate_deferrable_args(self, max_attempts, delay_seconds, debounce_seconds, debounce_always_delay, ttl_seconds):
        if max_attempts and (not isinstance(max_attempts, int)):
            raise TypeError('max_attempts must be int, received {}'.format(max_attempts))

        if debounce_seconds and not self.redis_client:
            raise ValueError('redis_client is required for debounce')

        if delay_seconds and debounce_seconds:
            raise ValueError('You cannot delay and debounce at the same time (debounce uses delay internally).')

        # This maximum delay is set for performance reasons
        # Do not remove unless you realllllly know what you're doing!
        if delay_seconds > 900 or debounce_seconds > 900:
            raise ValueError('Delay or debounce window cannot exceed 15 minutes (900 seconds)')

        if debounce_always_delay and not debounce_seconds:
            raise ValueError('debounce_always_delay is an option to debounce_seconds, which was not set. Probably a mistake.')

        if ttl_seconds:
            if delay_seconds > ttl_seconds or debounce_seconds > ttl_seconds:
                raise ValueError('delay_seconds or debounce_seconds must be less than ttl_seconds')

    def _deferrable(self, method, error_classes=None, max_attempts=None,
                    delay_seconds=None, debounce_seconds=False, debounce_always_delay=False, ttl_seconds=None):
        self._validate_deferrable_args(max_attempts, delay_seconds, debounce_seconds, debounce_always_delay, ttl_seconds)

        def later(*args, **kwargs):
            item = build_later_item(method, *args, **kwargs)
            item.update({
                'error_classes': dumps(error_classes),
                'attempts': 0,
                'max_attempts': max_attempts
            })
            if ttl_seconds:
                add_ttl_metadata_to_item(item, ttl_seconds)

            seconds_to_delay = delay_seconds or debounce_seconds
            if debounce_seconds:
                debounce_strategy, seconds_to_delay = get_debounce_strategy(self.redis_client, item, debounce_seconds, debounce_always_delay)
                if debounce_strategy == DebounceStrategy.SKIP:
                    self._emit('debounce_hit', item)
                    return

                self._emit('debounce_miss', item)

                if debounce_strategy == DebounceStrategy.PUSH_NOW:
                    set_last_push_time(self.redis_client, item, time.time(), debounce_seconds)
                elif debounce_strategy == DebounceStrategy.PUSH_DELAYED:
                    set_last_push_time(self.redis_client, item, time.time() + seconds_to_delay, debounce_seconds)
                    set_debounce_key(self.redis_client, item, seconds_to_delay)

            item['delay'] = seconds_to_delay or None

            for producer_consumer in self._metadata_producer_consumers:
                producer_consumer._apply_metadata_to_item(item)

            self.backend.queue.push(item)
            self._emit('push', item)

        method.later = later
        return method