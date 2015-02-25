class EventHandlerRegistrar(object):
    def __init__(self, queue):
        self._queue = queue
        self._handlers = []

        self.create_proxy_method('on_pop')
        self.create_proxy_method('on_push')
        self.create_proxy_method('on_complete')
        self.create_proxy_method('on_success')
        self.create_proxy_method('on_error')
        self.create_proxy_method('on_retry')
        self.create_proxy_method('on_expire')
        self.create_proxy_method('on_operation_error')
        self.create_proxy_method('on_empty')
        self.create_proxy_method('on_delay_pop')
        self.create_proxy_method('on_debounce_hit')
        self.create_proxy_method('on_debounce_miss')

    def register(self, handler):
        """Registers a handler to receive events."""
        if handler not in self._handlers:
            self._handlers.append(handler)
            if hasattr(handler, 'on_register'):
                handler.on_register(self._queue)

    def create_proxy_method(self, name):
        def proxy_method(*args, **kwargs):
            for handler in self._handlers:
                if hasattr(handler, name):
                    getattr(handler, name)(*args, **kwargs)
        setattr(self, name, proxy_method)
