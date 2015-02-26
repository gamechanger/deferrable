from redis import StrictRedis

from deferrable.backend.dockets import DocketsBackend

r = StrictRedis()
b = DocketsBackend(r)
q = b.for_group('test')

@q.deferrable
def foo():
    print 'WOOT'

foo.later()
q.run_once()
