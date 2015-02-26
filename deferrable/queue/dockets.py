from __future__ import absolute_import

from copy import deepcopy

import dockets.queue
import dockets.error_queue

from . import Queue

PUSH_KWARGS_KEYS = ['delay']

class DocketsQueue(Queue):
    def __init__(self, redis_client, queue_name):
        self.queue = dockets.queue.Queue(redis_client,
                                         queue_name,
                                         use_error_queue=True,
                                         wait_time=3,
                                         timeout=300)

    def make_error_queue(self):
        return DocketsErrorQueue(self.queue)

    def __len__(self):
        return self.queue.queued()

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

class DocketsErrorQueue(Queue):
    def __init__(self, parent_dockets_queue):
        self.queue = dockets.error_queue.ErrorQueue(parent_dockets_queue)

    def __len__(self):
        return self.queue.length()

    def _push(self, item):
        self.queue.queue_error(item)

    def _pop(self):
        error_ids = self.queue.error_ids()
        if error_ids:
            error = self.queue.error(error_id)
            self.queue.delete_error(error_id)
            return error, error.get('item')
        return None, None

    def _complete(self, envelope):
        error_id = envelope.get('id')
        if not error_id:
            raise AttributeError('Error item has no id field: {}'.format(envelope))
        self.queue.delete_error(error_id)
