from uuid import uuid1

from unittest import TestCase
from deferrable.backoff import apply_exponential_backoff

class TestBackoff(TestCase):
    """Apologies for how annoying these tests will be if the backoff constants
    are changed. Testing the actual value felt like a better idea than testing
    that the math is performed the same way on both sides."""

    def setUp(self):
        self.item = {'id': uuid1()}

    def test_apply_exponential_backoff_one_attempt(self):
        self.item['attempts'] = 1
        apply_exponential_backoff(self.item)
        self.assertEqual(self.item['delay'], 4)

    def test_apply_exponential_backoff_three_attempts(self):
        self.item['attempts'] = 2
        apply_exponential_backoff(self.item)
        self.assertEqual(self.item['delay'], 10)
