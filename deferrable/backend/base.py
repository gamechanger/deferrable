class BackendFactory(object):
    """Abstract class for creating an implementation-specific
    BackendFactory. Your subclass should override the
    `_create_backend_for_group` private method."""

    def _create_backend_for_group(self, group, *args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def _queue_name(group):
        base = 'deferrable'
        if group:
            return '{}_{}'.format(base, group)
        return base

    def create_backend_for_group(self, group, *args, **kwargs):
        return self._create_backend_for_group(group, *args, **kwargs)

class Backend(object):
    def __init__(self, group, queue, error_queue):
        self.group = group
        self.queue = queue
        self.error_queue = error_queue
