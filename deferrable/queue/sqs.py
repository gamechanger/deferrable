from __future__ import absolute_import

from boto.sqs.message import Message

from .base import Queue
from ..pickling import dumps, loads

class SQSQueue(Queue):
    FIFO = False

    def __init__(self, sqs_connection, queue_name, visibility_timeout, wait_time, create_if_missing=False):
        self.sqs_connection = sqs_connection
        self.queue_name = queue_name
        self.visibility_timeout = visibility_timeout
        self.wait_time = wait_time
        self.create_if_missing = create_if_missing

        self.queue = self._get_queue_instance()

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
        self.queue.write(message, delay_seconds=item.get('delay') or None)

    def _pop(self):
        message = self.queue.read(visibility_timeout=self.visibility_timeout,
                                  wait_time_seconds=self.wait_time)
        if not message:
            return None, None
        return message, loads(message.get_body())

    def _complete(self, envelope):
        self.sqs_connection.delete_message(self.queue, envelope)

    def _flush(self):
        self.sqs_connection.purge_queue(self.queue)

    def _stats(self):
        attributes = self.queue.get_attributes()
        return {'available': int(attributes['ApproximateNumberOfMessages']),
                'in_flight': int(attributes['ApproximateNumberOfMessagesNotVisible']),
                'delayed': int(attributes['ApproximateNumberOfMessagesDelayed'])}
