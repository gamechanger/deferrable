from __future__ import absolute_import

import logging
from uuid import uuid1

import dockets.queue
import dockets.error_queue

from .base import Queue

PUSH_KWARGS_KEYS = ['delay']

class DocketsQueue(Queue):
    def __init__(self, redis_client, queue_name, wait_time, timeout):
        self.queue = dockets.queue.Queue(redis_client,
                                         queue_name,
                                         use_error_queue=True,
                                         wait_time=wait_time,
                                         timeout=timeout)

    def make_error_queue(self):
        return DocketsErrorQueue(self.queue)

    def _push(self, item):
        push_kwargs = {}
        for key in PUSH_KWARGS_KEYS:
            if key in item:
                push_kwargs[key] = item[key]
        self.queue.push(item, **push_kwargs)

    def _pop(self):
        envelope = self.queue.pop()
        if envelope:
            return envelope, envelope.get('item')
        return None, None

    def _complete(self, envelope):
        return self.queue.complete(envelope)

    def _flush(self):
        while True:
            envelope, item = self._pop()
            if envelope is None:
                break
            self._complete(envelope)

    def _stats(self):
        return {'items_available': self.queue.queued(),
                'items_in_flight': self.queue.working(),
                'items_delayed': self.queue.delayed()}

class DocketsErrorQueue(Queue):
    FIFO = False
    SUPPORTS_DELAY = False

    def __init__(self, parent_dockets_queue):
        self.queue = dockets.error_queue.ErrorQueue(parent_dockets_queue)

    def _push(self, item):
        """This error ID dance is Dockets-specific, since we need the ID
        to interface with the hash error queue. Other backends shouldn't
        need to do this and should use the envelope properly instead."""
        try:
            error_id = item['error']['id']
        except KeyError:
            logging.warn('No error ID found for item, will generate and add one: {}'.format(item))
            error_id = str(uuid1())
            item.setdefault('error', {})['id'] = error_id
        self.queue.queue_error_item(error_id, item)

    def _pop(self):
        """Dockets Error Queues are not actually queues, they're hashes. There's no way
        for us to implement a pure pop that doesn't expose us to the risk of dropping
        data. As such, we're going to return the first error in that hash but not actually
        remove it until we call `_complete` later on. This keeps our data safe but may
        deliver errors multiple times. That should be okay."""
        error_ids = self.queue.error_ids()
        if error_ids:
            error_id = error_ids[0]
            error = self.queue.error(error_id)
            return error, error
        return None, None

    def _complete(self, envelope):
        error_id = envelope['error']['id']
        if not error_id:
            raise AttributeError('Error item has no id field: {}'.format(envelope))
        self.queue.delete_error(error_id)

    def _flush(self):
        for error_id in self.queue.error_ids():
            self.queue.delete_error(error_id)

    def _stats(self):
        return {'items_available': self.queue.length()}
