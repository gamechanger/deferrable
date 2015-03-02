from .pickling import load, dump

class MetadataProducerConsumer(object):
    """Defines a class which applies metadata to
    a queue item and receives the same metadata back on the consumer
    to consume it. This is useful for passing context from the
    producer to the consumer, e.g. correlation IDs.

    Requires a NAMESPACE which is used to separate metadata available
    to different ProducerConsumers."""
    NAMESPACE = None

    def __init__(self):
        if self.NAMESPACE is None:
            raise ValueError('NAMESPACE must be provided')

    def produce_metadata(self):
        """Return metadata to be applied to the queue item and consumed
        on the consumer side by `consume_metadata`."""
        pass

    def consume_metadata(self, metadata):
        """Receives the same metadata dict returned by the producer."""
        pass

    def _apply_metadata_to_item(self, item):
        item.setdefault('metadata', {})[self.NAMESPACE] = dump(self.produce_metadata())

    def _consume_metadata_from_item(self, item):
        metadata = item.get('metadata', {}).get(self.NAMESPACE)
        self.consume_metadata(load(metadata))
