from __future__ import absolute_import

from uuid import uuid1
from collections import OrderedDict

from boto.sqs.message import Message

from .base import Queue
from ..pickling import dumps, loads

class SQSQueue(Queue):
    FIFO = False
    MAX_PUSH_BATCH_SIZE = 10
    MAX_POP_BATCH_SIZE = 10
    MAX_COMPLETE_BATCH_SIZE = 10

    def __init__(self, sqs_connection_thunk, queue_name, visibility_timeout, wait_time, create_if_missing=False):
        self.sqs_connection_thunk = sqs_connection_thunk
        self.queue_name = queue_name
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time
        self.create_if_missing = create_if_missing

        self._sqs_connection = None
        self._queue = None

    @property
    def sqs_connection(self):
        if self._sqs_connection is None:
            self._sqs_connection = self.sqs_connection_thunk()
        return self._sqs_connection

    @property
    def queue(self):
        if self._queue is None:
            self._queue = self._get_queue_instance()
        return self._queue

    def _get_queue_instance(self):
        instance = self.sqs_connection.get_queue(self.queue_name)
        if instance is None and self.create_if_missing:
            instance = self.sqs_connection.create_queue(self.queue_name, visibility_timeout=self.visibility_timeout)
        if not instance:
            raise ValueError('No queue found with name {}'.format(self.queue_name))
        return instance

    def _slow_flush(self):
        """We need this during testing because SQS limits us to
        one proper flush per 60 seconds."""
        stored_wait_time = self.wait_time
        self.wait_time = None
        while True:
            envelope, item = self._pop()
            if envelope:
                self._complete(envelope)
            else:
                break
        self.wait_time = stored_wait_time

    def _push(self, item):
        message = Message()
        message.set_body(dumps(item))
        return self.queue.write(message, delay_seconds=item.get('delay') or None)

    def _push_batch(self, items):
        id_map = OrderedDict()
        payloads = []
        for item in items:
            message = Message()
            message.set_body(dumps(item))
            new_message_id = str(uuid1())
            id_map[new_message_id] = item
            payloads.append((new_message_id, message.get_body_encoded(), item.get('delay') or 0))
        response = self.queue.write_batch(payloads)
        success_ids = {success['id'] for success in response.results}
        return [(item, item_id in success_ids)
                for item_id, item in id_map.iteritems()]

    def _pop(self):
        message = self.queue.read(visibility_timeout=self.visibility_timeout,
                                  wait_time_seconds=self.wait_time)
        if not message:
            return None, None
        return message, loads(message.get_body())

    def _pop_batch(self, batch_size):
        messages = self.queue.get_messages(num_messages=batch_size,
                                           visibility_timeout=self.visibility_timeout,
                                           wait_time_seconds=self.wait_time)
        batch = []
        for message in messages:
            batch.append((message, loads(message.get_body())))
        return batch

    def _touch(self, envelope, seconds):
        return envelope.change_visibility(seconds)

    def _complete(self, envelope):
        return self.sqs_connection.delete_message(self.queue, envelope)

    def _complete_batch(self, envelopes):
        response = self.sqs_connection.delete_message_batch(self.queue, envelopes)
        id_map = {success['id']: True
                  for success in response.results}
        id_map.update({failure['id']: False
                       for failure in response.errors})
        return [(envelope, id_map[envelope.id]) for envelope in envelopes]

    def _flush(self):
        self.sqs_connection.purge_queue(self.queue)

    def _stats(self):
        attributes = self.queue.get_attributes()
        return {'available': int(attributes['ApproximateNumberOfMessages']),
                'in_flight': int(attributes['ApproximateNumberOfMessagesNotVisible']),
                'delayed': int(attributes['ApproximateNumberOfMessagesDelayed'])}
