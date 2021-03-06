from unittest import TestCase
import os
import time

from redis import StrictRedis

from deferrable.debounce import (DebounceStrategy, _debounce_key, _last_push_key,
                                 set_debounce_keys_for_push_now, set_debounce_keys_for_push_delayed,
                                 get_debounce_strategy)
from deferrable.redis import initialize_redis_client

class TestDebounce(TestCase):
    def setUp(self):
        self.redis_client = initialize_redis_client(StrictRedis(host=os.getenv("DEFERRABLE_TEST_REDIS_HOST","redis")))
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

    def test_set_debounce_keys_for_push_now(self):
        set_debounce_keys_for_push_now(self.redis_client, self.item, 0.01)
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
        set_debounce_keys_for_push_now(self.redis_client, self.item, 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, False)
        self.assertEqual(strategy, DebounceStrategy.PUSH_DELAYED)
        self.assertEqual(delay_time, 1)

    def test_debounce_strategy_push_set_always_delay(self):
        set_debounce_keys_for_push_now(self.redis_client, self.item, 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, True)
        self.assertEqual(strategy, DebounceStrategy.PUSH_DELAYED)
        self.assertEqual(delay_time, 1)

    def test_debounce_strategy_debounce_set(self):
        set_debounce_keys_for_push_delayed(self.redis_client, self.item, 1, 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, False)
        self.assertEqual(strategy, DebounceStrategy.SKIP)
        self.assertEqual(delay_time, 0)

    def test_debounce_strategy_debounce_set_always_delay(self):
        set_debounce_keys_for_push_delayed(self.redis_client, self.item, 1, 1)
        strategy, delay_time = get_debounce_strategy(self.redis_client, self.item, 1, True)
        self.assertEqual(strategy, DebounceStrategy.SKIP)
        self.assertEqual(delay_time, 0)
