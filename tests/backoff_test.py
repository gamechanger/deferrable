from uuid import uuid1

from unittest import TestCase
from deferrable.backoff import apply_exponential_backoff_options, apply_exponential_backoff_delay
from deferrable.delay import MAXIMUM_DELAY_SECONDS

class TestBackoff(TestCase):
    """Apologies for how annoying these tests will be if the backoff constants
    are changed. Testing the actual value felt like a better idea than testing
    that the math is performed the same way on both sides."""

    def setUp(self):
        self.item = {'id': uuid1()}

    def test_apply_exponential_backoff_options_enable(self):
        apply_exponential_backoff_options(self.item, True)
        self.assertEqual(self.item['use_exponential_backoff'], True)

    def test_apply_exponential_backoff_options_disable(self):
        apply_exponential_backoff_options(self.item, False)
        self.assertEqual(self.item['use_exponential_backoff'], False)

    def test_apply_exponential_backoff_delay_one_attempt_enabled(self):
        self.item['attempts'] = 1
        self.item['use_exponential_backoff'] = True
        apply_exponential_backoff_delay(self.item)
        self.assertEqual(self.item['delay'], 4)

    def test_apply_exponential_backoff_delay_one_attempt_disabled(self):
        self.item['attempts'] = 1
        self.item['use_exponential_backoff'] = False
        apply_exponential_backoff_delay(self.item)
        self.assertIsNone(self.item.get('delay'))

    def test_apply_exponential_backoff_delay_three_attempts(self):
        self.item['attempts'] = 3
        self.item['use_exponential_backoff'] = True
        apply_exponential_backoff_delay(self.item)
        self.assertEqual(self.item['delay'], 10)

    def test_apply_exponential_backoff_limited_by_max_delay(self):
        self.item['attempts'] = 100
        self.item['use_exponential_backoff'] = True
        apply_exponential_backoff_delay(self.item)
        self.assertEqual(self.item['delay'], MAXIMUM_DELAY_SECONDS)
