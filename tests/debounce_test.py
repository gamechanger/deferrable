from unittest import TestCase
import time

from redis import StrictRedis

from deferrable.debounce import (DebounceStrategy, _debounce_key, _last_push_key,
                                 set_last_push_time, set_debounce_key, get_debounce_strategy)

class TestDebounce(TestCase):
    def setUp(self):
        self.redis_client = StrictRedis()
        self.item = {
            'method': 'pickled_method',
            'args': 'pickled_args',
            'kwargs': 'pickled_kwargs'
        }

    def tearDown(self):
        self.redis_client.delete(_debounce_key(self.item))
        self.redis_client.delete(_last_push_key(self.item))

    def test_debounce_key(self):
        expected = 'debounce.pickled_method.pickled_args.pickled_kwargs'
        self.assertEqual(expected, _debounce_key(self.item))

    def test_last_push_key(self):
        expected = 'last_push.pickled_method.pickled_args.pickled_kwargs'
        self.assertEqual(expected, _last_push_key(self.item))

    def test_set_last_push_time(self):
        set_last_push_time(self.redis_client, self.item, 1, 0.01)
        self.assertIsNotNone(self.redis_client.get(_last_push_key(self.item)))
        time.sleep(0.03)
        self.assertIsNone(self.redis_client.get(_last_push_key(self.item)))

    def test_debounce_strategy_first_time(self):
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, False)
        self.assertEqual(strategy, DebounceStrategy.PUSH_NOW)
        self.assertEqual(delay_time, 0)

    def test_debounce_strategy_first_time_always_delay(self):
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, True)
        self.assertEqual(strategy, DebounceStrategy.PUSH_DELAYED)
        self.assertEqual(delay_time, 1)

    def test_debounce_strategy_push_set(self):
        set_last_push_time(self.redis_client, self.item, time.time(), 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, False)
        self.assertEqual(strategy, DebounceStrategy.PUSH_DELAYED)
        self.assertGreater(delay_time, 0)
        self.assertLess(delay_time, 1)

    def test_debounce_strategy_push_set_always_delay(self):
        set_last_push_time(self.redis_client, self.item, time.time(), 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, True)
        self.assertEqual(strategy, DebounceStrategy.PUSH_DELAYED)
        self.assertEqual(delay_time, 1)

    def test_debounce_strategy_debounce_set(self):
        set_debounce_key(self.redis_client, self.item, 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, False)
        self.assertEqual(strategy, DebounceStrategy.SKIP)
        self.assertEqual(delay_time, 0)

    def test_debounce_strategy_debounce_set_always_delay(self):
        set_debounce_key(self.redis_client, self.item, 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, True)
        self.assertEqual(strategy, DebounceStrategy.SKIP)
        self.assertEqual(delay_time, 0)
