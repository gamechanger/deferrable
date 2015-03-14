"""Unified pickling imports throughout the project. Any module in this
project, or any external code which needs direct access to the serialized
deferred item, should use the functions defined here instead of importing
`pickle` or `cPickle` directly."""

import cPickle as pickle

def loads(string):
    if string is None:
        return None
    return pickle.loads(string.decode('string_escape'))

def dumps(obj):
    return pickle.dumps(obj).encode('string_escape')

def pretty_unpickle(item):
    method, args, kwargs = unpickle_method_call(item)
    return str({
        'method': method.func_code.co_name,
        'filename': method.func_code.co_filename,
        'lineno': method.func_code.co_firstlineno,
        'args': str(args),
        'kwargs': str(kwargs)
    })

def build_later_item(method, *args, **kwargs):
    return {
        'args': dumps(args),
        'kwargs': dumps(sorted(kwargs.items())),
        'method': dumps(method)
    }

def unpickle_method_call(item):
    if 'object' in item:
        obj = loads(item['object'])
        method = getattr(obj, item['method'])
    else:
        method = loads(item['method'])
    args = loads(item['args'])
    kwargs = loads(item['kwargs'])
    if isinstance(kwargs, list):
        kwargs = dict(kwargs)
    return method, args, kwargs
