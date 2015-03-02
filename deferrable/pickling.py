import cPickle as pickle

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
        'args': pickle.dumps(args).encode('string_escape'),
        'kwargs': pickle.dumps(sorted(kwargs.items())).encode('string_escape'),
        'method': pickle.dumps(method)
    }

def unpickle_method_call(item):
    if 'object' in item:
        obj = pickle.loads(item['object'])
        method = getattr(obj, item['method'])
    else:
        method = pickle.loads(item['method'])
    args = pickle.loads(item['args'].decode('string_escape'))
    kwargs = pickle.loads(item['kwargs'].decode('string_escape'))
    if isinstance(kwargs, list):
        kwargs = dict(kwargs)
    return method, args, kwargs
