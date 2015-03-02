class BackendFactory(object):
    def create_backend_for_group(self, group, *args, **kwargs):
        raise NotImplementedError()

class Backend(object):
    def __init__(self, group, queue, error_queue):
        self.group = group
        self.queue = queue
        self.error_queue = error_queue
