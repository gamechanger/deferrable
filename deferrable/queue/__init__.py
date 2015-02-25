import time
import pickle

from dockets.queue import Queue as DocketsQueue

from ..registrar import EventHandlerRegistrar

class DeferrableQueue(object):
    def __init__(self, backed_queue, redis_client):
        self.backed_queue = backed_queue
        self.redis_client = redis_client

        self._registrar = EventHandlerRegistrar(self.backed_queue)
        self._item_transformers = []

    @staticmethod
    def _unpickle(item):
        # Extract the method call details.
        if 'object' in item:
            obj = pickle.loads(item['object'])
            method = getattr(obj, item['method'])
        else:
            method = pickle.loads(item['method'])
        args = pickle.loads(item['args'].decode('string_escape'))
        kwargs = pickle.loads(item['kwargs'].decode('string_escape'))
        if isinstance(kwargs, list):
            kwargs = dict(kwargs)
        return method, args, kwargs

    def _validate_deferrable_args(self, max_attempts, delay_seconds, debounce_seconds, debounce_always_delay, ttl_seconds):
        if max_attempts and (not isinstance(max_attempts, int)):
            raise TypeError('max_attempts must be int, received {}'.format(max_attempts))

        if debounce_seconds and not self.redis_client:
            raise ValueError('redis_client is required for debounce')

        if delay_seconds and debounce_seconds:
            raise ValueError('You cannot delay and debounce at the same time (debounce uses delay internally).')

        if delay_seconds > 900 or debounce_seconds > 900:
            raise ValueError('Delay or debounce window cannot exceed 15 minutes (900 seconds)')

        if debounce_always_delay and not debounce_seconds:
            raise ValueError('debounce_always_delay is an option to debounce_seconds, which was not set. Probably a mistake.')

        if ttl_seconds:
            if delay_seconds > ttl_seconds or debounce_seconds > ttl_seconds:
                raise ValueError('delay_seconds or debounce_seconds must be less than ttl_seconds')

    def _apply_queue_item_transformers(self, item):
        for transformer in self._item_transformers:
            transformer(item)

    def _debounce_key(item):
        return u"debounce.{}.{}.{}".format(item['method'], item['args'], item['kwargs'])

    def _last_push_key(item):
        return u"last_push.{}.{}.{}".format(item['method'], item['args'], item['kwargs'])

    def _get_debounce_strategy(item, debounce_seconds, debounce_always_delay):
        if self.redis_client.get(_debounce_key(item)):
            return DebounceStrategy.SKIP, 0

        if debounce_always_delay:
            return DebounceStrategy.PUSH_DELAYED, debounce_seconds

        last_push_time = self.redis_client.get(_last_push_key(item))
        if not last_push_time:
            return DebounceStrategy.PUSH_NOW, 0

        seconds_since_last_push = time.time() - float(last_push_time)
        if seconds_since_last_push > debounce_seconds:
            return DebounceStrategy.PUSH_NOW, 0

        return DebounceStrategy.PUSH_DELAYED, debounce_seconds - seconds_since_last_push

    def _set_last_push_time(item, time_to_set, delay_seconds):
        """Set a key in Redis indicating the last time this item was potentially
        available inside a non-delay queue. Expires after 2*delay period to
        keep Redis clean. The 2* ensures that the key would have been stale at
        the period it is reaped."""
        self.redis_client.set(_last_push_key(item), time_to_set, ex=2*delay_seconds)

    def _set_debounce_key(item, expire_seconds):
        self.redis_client.set(_debounce_key(item), '_', px=int(expire_seconds*1000))

    def _deferrable(self, method, error_classes=None, max_attempts=None,
                    delay_seconds=None, debounce_seconds=False,
                    debounce_always_delay=False, ttl_seconds=None):
        self._validate_deferrable_args(max_attempts, delay_seconds, debounce_seconds, debounce_always_delay, ttl_seconds)

        def later(*args, **kwargs):
            item = {
                'args': pickle.dumps(args).encode('string_escape'),
                'kwargs': pickle.dumps(sorted(kwargs.items())).encode('string_escape'),
                'method': pickle.dumps(method)
            }
            if ttl_seconds:
                item['ttl_seconds'] = ttl_seconds
                item['item_queued_timestamp'] = time.time()
            self._apply_queue_item_transformers(item)

            seconds_to_delay = delay_seconds or debounce_seconds
            if debounce_seconds:
                debounce_strategy, seconds_to_delay = _get_debounce_strategy(item, debounce_seconds, debounce_always_delay)
                if debounce_strategy == DebounceStrategy.SKIP:
                    self.registrar.on_debounce_hit(queue=self, item=item)
                    return

                self.registrar.on_debounce_miss(queue=self, item=item)

                if debounce_strategy == DebounceStrategy.PUSH_NOW:
                    _set_last_push_time(item, time.time(), debounce_seconds)
                elif debounce_strategy == DebounceStrategy.PUSH_DELAYED:
                    _set_last_push_time(item, time.time() + seconds_to_delay, debounce_seconds)
                    _set_debounce_key(item, seconds_to_delay)

            self.backed_queue.push(item, error_classes=error_classes, max_attempts=max_attempts, delay=seconds_to_delay or None)

        method.later = later
        return method

    def deferrable(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            method = args[0]
            return self._deferrable(method)
        return lambda method: self._deferrable(method, *args, **kwargs)

    def run_once(self):
        item = self.backed_queue.pop()
        if not item:
            return
        method, args, kwargs = self._unpickle(item)
        method(*args, **kwargs)
        self.backed_queue.complete(item)

    def add_item_transformer(self, transformer):
        self._item_transformers.append(transformer)

    def add_event_handler(self, handler):
        self.registrar.register(handler)

    def stats(self):
        return self.backed_queue.stats()
