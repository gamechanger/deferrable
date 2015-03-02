class BackendFactory(object):
    def create_backend_for_group(self, group, *args, **kwargs):
        raise NotImplementedError()

class Backend(object):
    def __init__(self, queue, error_queue):
        self.queue = queue
        self.error_queue = error_queue
