import time
from uuid import uuid1

from unittest import TestCase
from deferrable.ttl import add_ttl_metadata_to_item, item_is_expired

class TestTTL(TestCase):
    def setUp(self):
        self.item = {'id': uuid1()}

    def test_add_ttl_metadata_to_item(self):
        add_ttl_metadata_to_item(self.item, 1)
        self.assertTrue('item_queued_timestamp' in self.item)
        self.assertEqual(self.item['ttl_seconds'], 1)

    def test_item_is_expired_no_ttl_metadata(self):
        self.assertFalse(item_is_expired(self.item))

    def test_item_is_expired_not_yet(self):
        add_ttl_metadata_to_item(self.item, 1)
        self.assertFalse(item_is_expired(self.item))

    def test_item_is_expired_time_elapsed(self):
        add_ttl_metadata_to_item(self.item, 1)
        time.sleep(1.01)
        self.assertTrue(item_is_expired(self.item))
