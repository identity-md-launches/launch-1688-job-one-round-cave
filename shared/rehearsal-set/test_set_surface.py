"""Real archived replay and synthetic refusal fixtures; no network or new evidence."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import set_surface as tool


class SetSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.saved, self.plan, self.choices, self.proofs = tool.demo_inputs()
        self.label = self.plan['calls'][0]['id']

    def run_check(self):
        return tool.evaluate(self.saved, self.plan, self.choices, self.proofs)

    def test_real_same_block_join(self):
        before = copy.deepcopy((self.saved, self.plan, self.choices, self.proofs))
        result = self.run_check()
        self.assertEqual(result['verdict'], 'aligned')
        self.assertEqual(result['decoded_calls'][0]['returns'][0]['value'],
                         '285939607966355541747129965')
        self.assertEqual(result['code_checks'][0]['proof_anchor'], 'unanchored-rpc-header')
        self.assertEqual(before, (self.saved, self.plan, self.choices, self.proofs))

    def test_changed_expected_return_withholds(self):
        self.plan['calls'][0]['expected_return'] = '0x'
        result = self.run_check()
        self.assertEqual(result['verdict'], 'withheld')
        self.assertIsNone(result['decoded_calls'])
        self.assertEqual(result['code_checks'], [])

    def test_missing_sender_never_filled(self):
        del self.saved['observations'][0]['observation']['call']['from']
        with self.assertRaisesRegex(ValueError, 'explicit sender'):
            self.run_check()

    def test_same_changed_block_labels_do_not_relabel_proof(self):
        self.plan['block']['number'] = hex(int(self.plan['block']['number'], 16) + 1)
        self.saved['observations'][0]['observation']['block']['number'] = self.plan['block']['number']
        result = self.run_check()
        self.assertEqual(result['binding_verdict'], 'bound')
        self.assertEqual(result['verdict'], 'withheld')
        self.assertIn('same_block_number', result['code_checks'][0]['failed_checks'])
        self.assertIsNone(result['decoded_calls'])

    def test_wrong_selector_and_layout_withhold(self):
        self.choices[self.label]['signature'] = 'totalSupply()'
        result = self.run_check()
        self.assertEqual(result['verdict'], 'withheld')
        self.assertIn('call_selector_matches', result['code_checks'][0]['failed_checks'])

    def test_corrupt_proof_rejected(self):
        raw = self.proofs[self.label]['header_rlp']
        self.proofs[self.label]['header_rlp'] = raw[:-2] + ('01' if raw[-2:] != '01' else '02')
        with self.assertRaises(ValueError):
            self.run_check()

    def test_exact_choice_and_proof_coverage(self):
        for name in ('choices', 'proofs'):
            current = getattr(self, name)
            for value in ({}, dict(current, extra=current[self.label])):
                setattr(self, name, value)
                with self.assertRaises(ValueError):
                    self.run_check()
            setattr(self, name, current)

    def test_extra_choice_fields_refused(self):
        self.choices[self.label]['gas'] = '0x5208'
        with self.assertRaises(ValueError):
            self.run_check()

    def test_real_three_member_set_with_older_code_withholds_all(self):
        saved = tool.sets.binding.read_json(tool.HERE / 'zto-set-evidence.json')
        plan = tool.sets.binding.read_json(tool.HERE / 'zto-set-plan.json')
        choices = {item['id']: {
            'signature': 'balanceOf(address)' if 'balance' in item['id'] else 'totalSupply()',
            'return_types': ['uint256']} for item in plan['calls']}
        proofs = {item['id']: self.proofs[self.label] for item in plan['calls']}
        result = tool.evaluate(saved, plan, choices, proofs)
        self.assertEqual(result['binding_verdict'], 'bound')
        self.assertEqual(len(result['code_checks']), 3)
        self.assertEqual(result['code_checks'][0]['transport'],
                         saved['observations'][0]['observation']['transport'])
        self.assertEqual(result['verdict'], 'withheld')
        self.assertIsNone(result['decoded_calls'])

    def test_partial_success_is_not_released(self):
        saved = tool.sets.binding.read_json(tool.HERE / 'zto-set-evidence.json')
        plan = tool.sets.binding.read_json(tool.HERE / 'zto-set-plan.json')
        choices = {item['id']: self.choices[self.label] for item in plan['calls']}
        proofs = {item['id']: self.proofs[self.label] for item in plan['calls']}
        real = tool.surface.evaluate(self.proofs[self.label],
            self.saved['observations'][0]['observation'], 'balanceOf(address)', ['uint256'])
        # Mock only surface alignment to isolate the aggregation invariant.
        failed = dict(real, verdict='mismatch', failed_checks=['same_target'])
        with patch.object(tool.surface, 'evaluate', side_effect=[real, failed, real]):
            result = tool.evaluate(saved, plan, choices, proofs)
        self.assertEqual(result['verdict'], 'withheld')
        self.assertIsNone(result['decoded_calls'])

    def test_cli_no_network_and_option_pairing(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(tool.main(['--demo']), 0)
            self.assertEqual(json.loads(output.getvalue())['verdict'], 'aligned')
        for args in ([], ['--plan', 'missing.json'], ['--demo', '--plan', 'missing.json']):
            with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(tool.main(args), 1)
            self.assertEqual(out.getvalue(), '')

    def test_manifest_duplicates_and_workspace_escape(self):
        member = {'id': self.label, 'signature': 'balanceOf(address)', 'return_types': ['uint256'],
                  'proof': str(tool.HERE.parent / 'surface-return/zto-proof.json')}
        value = {'schema': 'set-surface-manifest-v1', 'members': [member, member]}
        with self.assertRaises(ValueError):
            tool.manifest(value)
        value['members'] = [dict(member, proof=str(Path.cwd().parent / 'outside.json'))]
        with self.assertRaises(ValueError):
            tool.manifest(value)

    def test_invalid_transport_not_silently_discarded(self):
        self.saved['observations'][0]['observation']['transport'] = {'verified': True}
        with self.assertRaises(ValueError):
            self.run_check()

    def test_valid_explicit_cli_manifest(self):
        import tempfile
        scratch = Path('test/scratch'); scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            folder = Path(folder)
            member = {'id': self.label, 'signature': 'balanceOf(address)', 'return_types': ['uint256'],
                      'proof': str(tool.HERE.parent / 'surface-return/zto-proof.json')}
            values = {'plan': self.plan, 'evidence': self.saved,
                      'manifest': {'schema': 'set-surface-manifest-v1', 'members': [member]}}
            args = []
            for key, value in values.items():
                path = folder / (key + '.json')
                path.write_text(json.dumps(value))
                args.extend(['--' + key, str(path)])
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(tool.main(args), 0)
            self.assertEqual(json.loads(out.getvalue())['verdict'], 'aligned')


if __name__ == '__main__':
    unittest.main()
