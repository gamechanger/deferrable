from unittest import TestCase
from mock import Mock

from deferrable.pickling import pretty_unpickle, build_later_item, unpickle_method_call

def test_method(*args, **kwargs):
    pass

class TestPickling(TestCase):
    def test_pickle_and_unpickle_item(self):
        item = build_later_item(test_method, 'a', b='c')
        method, args, kwargs = unpickle_method_call(item)
        self.assertEqual(method, test_method)
        self.assertEqual(args, ('a',))
        self.assertEqual(kwargs, {'b': 'c'})

    def test_pretty_unpickle(self):
        # Just a weak test to make sure it doesn't throw anything
        item = build_later_item(test_method, 'a', b='c')
        print pretty_unpickle(item)
