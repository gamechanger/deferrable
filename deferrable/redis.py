from pkg_resources import resource_string

from attrdict import AttrDict

LUA_SCRIPTS = ['get_debounce_keys', 'set_debounce_keys']

def initialize_redis_client(redis_client):
    if not redis_client:
        return redis_client
    scripts = AttrDict()
    for script in LUA_SCRIPTS:
        source = resource_string(__name__, 'lua/{}.lua'.format(script))
        scripts[script] = redis_client.register_script(source)
    setattr(redis_client, 'scripts', scripts)
    return redis_client
