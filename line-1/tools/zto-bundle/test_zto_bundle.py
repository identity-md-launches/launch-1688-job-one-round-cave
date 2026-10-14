"""Evidence transfer failures exercised against real historical pool data."""
import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import zto_bundle as b


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = b.h.review.read_json(b.h.review.DEFAULT_SNAPSHOT)
        cls.report = b.h.review.read_json(b.h.review.DEFAULT_REPORT)
        cls.policy = b.h.review.read_json(b.h.review.HERE / 'demo-policy.json')
        cls.bundle = b.pack(cls.snapshot, cls.report, cls.policy, '100000000', 'historical_demo')

    def redigest(self, value):
        value['bundle_sha256'] = b.h.review.digest(
            {k: v for k, v in value.items() if k != 'bundle_sha256'})

    def test_real_evidence_roundtrip_without_network(self):
        with patch.object(b.h.review.sizes.path.z, 'RPC', side_effect=AssertionError('network')):
            result = b.verify(json.loads(json.dumps(self.bundle)), self.policy)
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(int(result['block']['number'], 16), 26184260)
        self.assertEqual(result['minimum_output'], '1184.169088029408336486')

    def test_changed_report_refused_even_after_redigest(self):
        value = copy.deepcopy(self.bundle)
        value['report']['candidates'][1]['minimum_output_raw'] = '1'
        self.redigest(value)
        with self.assertRaises(ValueError):
            b.verify(value, self.policy)

    def test_valid_replacement_policy_requires_receiver_agreement(self):
        policy = copy.deepcopy(self.policy)
        policy['reference_block'] += 1
        policy['max_age_blocks'] += 1
        value = b.pack(self.snapshot, self.report, policy, '100000000')
        with self.assertRaisesRegex(ValueError, 'receiver policy'):
            b.verify(value, self.policy)
        self.assertEqual(b.verify(value, policy)['status'], 'accepted')

    def test_missing_and_extra_sources_refused(self):
        for key in ('snapshot', 'report', 'policy', 'handoff'):
            value = copy.deepcopy(self.bundle)
            del value[key]
            self.redigest(value)
            with self.assertRaises(ValueError):
                b.verify(value, self.policy)
        value = copy.deepcopy(self.bundle)
        value['transaction'] = {'data': 'not allowed'}
        self.redigest(value)
        with self.assertRaises(ValueError):
            b.verify(value, self.policy)

    def test_semantic_handoff_rewrite_refused_with_valid_digests(self):
        value = copy.deepcopy(self.bundle)
        value['handoff']['limitations'] = ['Guaranteed receipt.']
        value['handoff']['handoff_sha256'] = b.h.review.digest(
            {k: v for k, v in value['handoff'].items() if k != 'handoff_sha256'})
        self.redigest(value)
        with self.assertRaisesRegex(ValueError, 'exactly match'):
            b.verify(value, self.policy)

    def test_size_and_ambiguous_numbers_refused(self):
        for value in ({'oversized': 'x' * 100001}, {'float': 1.5}):
            with self.assertRaises(ValueError):
                b.bounded_copy(value)

    def test_boolean_cannot_impersonate_integer_chain_id(self):
        value = copy.deepcopy(self.bundle)
        value['handoff']['chain_id'] = True
        value['handoff']['handoff_sha256'] = b.h.review.digest(
            {k: v for k, v in value['handoff'].items() if k != 'handoff_sha256'})
        self.redigest(value)
        with self.assertRaises(ValueError):
            b.verify(value, self.policy)

    def test_cli_demo_is_offline_and_saves_bundle_not_receipt(self):
        with patch.object(b.h.review.sizes.path.z, 'RPC', side_effect=AssertionError('network')):
            with patch.object(b.h.review.sizes.path, 'save_json') as save:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(b.main(['--demo', '--save', 'test/scratch/bundle.json']), 0)
        self.assertEqual(save.call_args.args[1]['schema'], b.SCHEMA)
        self.assertEqual(json.loads(out.getvalue())['status'], 'accepted')

    def test_cli_requires_receiver_policy_and_never_saves_failure(self):
        with patch.object(b.h.review.sizes.path, 'save_json') as save:
            for args in (['--verify', 'test/scratch/bundle.json'],
                         ['--demo', '--amount', '1', '--save', 'test/scratch/bundle.json']):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(b.main(args), 1)
            save.assert_not_called()


if __name__ == '__main__':
    unittest.main()
