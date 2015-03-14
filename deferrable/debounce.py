"""Debouncing provides functions for delaying or skipping a queue `push`
subject to a specified debouncing constraint. When used with idempotent
operations, this provides a safe and consistent method of throttling
queue pushes within Deferrable itself.

The debouncing constraint is defined as follows:

If `debounce_always_delay` is `False`, items should be made available for
execution as quickly as possible subject to the constraint that the same
item be made available at most once per `debounce_seconds` seconds.

If 'debounce_always_delay` is `True`, the item will be always either be
skipped (debounced) or delayed by the full `debounce_seconds` amount. The
constraint that the item is processed at most once per `debounce_seconds` seconds
still holds."""

import time

class DebounceStrategy(object):
    PUSH_NOW = 1
    PUSH_DELAYED = 2
    SKIP = 3

def _debounce_key(item):
    return u"debounce.{}.{}.{}".format(item['method'], item['args'], item['kwargs'])

def _last_push_key(item):
    return u"last_push.{}.{}.{}".format(item['method'], item['args'], item['kwargs'])

def set_last_push_time(redis_client, item, time_to_set, delay_seconds):
    """Set a key in Redis indicating the last time this item was potentially
    available inside a non-delay queue. Expires after 2*delay period to
    keep Redis clean. The 2* ensures that the key would have been stale at
    the period it is reaped."""
    redis_client.set(_last_push_key(item), time_to_set, px=int(2*delay_seconds*1000))

def set_debounce_key(redis_client, item, expire_seconds):
    redis_client.set(_debounce_key(item), '_', px=int(expire_seconds*1000))

def get_debounce_strategy(redis_client, item, debounce_seconds, debounce_always_delay):
    if redis_client.get(_debounce_key(item)):
        return DebounceStrategy.SKIP, 0

    if debounce_always_delay:
        return DebounceStrategy.PUSH_DELAYED, debounce_seconds

    last_push_time = redis_client.get(_last_push_key(item))
    if not last_push_time:
        return DebounceStrategy.PUSH_NOW, 0

    seconds_since_last_push = time.time() - float(last_push_time)
    if seconds_since_last_push > debounce_seconds:
        return DebounceStrategy.PUSH_NOW, 0

    return DebounceStrategy.PUSH_DELAYED, debounce_seconds - seconds_since_last_push
