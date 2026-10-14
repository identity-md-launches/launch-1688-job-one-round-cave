"""Offline regression checks; mutations are synthetic, saved demo data is real."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import rehearsal_set as tool


class RehearsalSetTests(unittest.TestCase):
    def setUp(self):
        self.saved = tool.binding.read_json(tool.HERE / 'zto-set-evidence.json')
        self.plan = tool.binding.read_json(tool.HERE / 'zto-set-plan.json')

    def run_check(self):
        return tool.evaluate(self.saved, self.plan)

    def test_saved_real_set(self):
        result = self.run_check()
        self.assertEqual(result['verdict'], 'bound')
        self.assertEqual(result['matched_count'], 3)
        self.assertEqual(result['missing_ids'], [])
        self.assertEqual(len(result['evidence_sha256']), 64)

    def test_does_not_mutate_inputs(self):
        before = copy.deepcopy((self.saved, self.plan))
        self.run_check()
        self.assertEqual((self.saved, self.plan), before)

    def test_order_is_not_execution_order(self):
        self.saved['observations'].reverse()
        self.plan['calls'].reverse()
        self.assertEqual(self.run_check()['verdict'], 'bound')

    def test_missing_call_withholds_whole_set(self):
        missing = self.saved['observations'].pop()['id']
        result = self.run_check()
        self.assertEqual(result['verdict'], 'inconclusive')
        self.assertEqual(result['missing_ids'], [missing])
        self.assertEqual(result['matched_count'], 2)

    def test_unexpected_entry(self):
        extra = copy.deepcopy(self.saved['observations'][0])
        extra['id'] = 'unexpected'
        self.saved['observations'].append(extra)
        result = self.run_check()
        self.assertEqual(result['verdict'], 'mismatch')
        self.assertEqual(result['unexpected_ids'], ['unexpected'])

    def test_duplicate_ids_rejected_in_both_inputs(self):
        for container, name in ((self.saved, 'observations'), (self.plan, 'calls')):
            with self.subTest(name=name):
                container[name].append(copy.deepcopy(container[name][0]))
                with self.assertRaisesRegex(ValueError, 'duplicate id'):
                    self.run_check()
                container[name].pop()

    def test_same_call_cannot_be_counted_twice(self):
        self.plan['calls'][1]['call'] = copy.deepcopy(self.plan['calls'][0]['call'])
        with self.assertRaisesRegex(ValueError, 'duplicate planned call'):
            self.run_check()

    def test_wrong_identifier_does_not_remap_evidence(self):
        self.saved['observations'][0]['id'], self.saved['observations'][1]['id'] = (
            self.saved['observations'][1]['id'], self.saved['observations'][0]['id'])
        self.assertEqual(self.run_check()['verdict'], 'mismatch')

    def test_changed_block_fields(self):
        for field in ('number', 'hash', 'timestamp'):
            with self.subTest(field=field):
                saved = copy.deepcopy(self.saved)
                block = saved['observations'][0]['observation']['block']
                block[field] = (hex(int(block[field], 16) + 1) if field != 'hash'
                                else '0x' + format(int(block[field], 16) ^ 1, '064x'))
                self.assertEqual(tool.evaluate(saved, self.plan)['verdict'], 'mismatch')

    def test_changed_caller_target_data_value(self):
        mutations = {'from': tool.core.TOKENS['IMD'], 'to': tool.core.TOKENS['IMD'],
                     'data': '0x18160ddd00', 'value': '0x1'}
        for field, value in mutations.items():
            with self.subTest(field=field):
                saved = copy.deepcopy(self.saved)
                saved['observations'][0]['observation']['call'][field] = value
                self.assertEqual(tool.evaluate(saved, self.plan)['verdict'], 'mismatch')

    def test_missing_sender_never_defaults(self):
        del self.saved['observations'][0]['observation']['call']['from']
        self.assertEqual(self.run_check()['verdict'], 'inconclusive')

    def test_changed_return(self):
        self.saved['observations'][0]['observation']['outcome']['result'] = '0x' + '00' * 32
        self.assertEqual(self.run_check()['verdict'], 'mismatch')

    def test_revert_is_not_success(self):
        self.saved['observations'][0]['observation']['outcome'] = {
            'error': {'code': 3, 'message': 'execution reverted', 'data': '0x'}}
        self.assertEqual(self.run_check()['verdict'], 'mismatch')

    def test_rpc_failure_is_inconclusive(self):
        self.saved['observations'][0]['observation']['outcome'] = {
            'error': {'code': -32000, 'message': 'provider unavailable'}}
        self.assertEqual(self.run_check()['verdict'], 'inconclusive')

    def test_bad_return_interpretation_is_inconclusive(self):
        self.saved['observations'][0]['observation']['outcome'] = {'result': '0x01'}
        self.assertEqual(self.run_check()['verdict'], 'inconclusive')

    def test_expected_false_only_means_bytes_match(self):
        entry = self.saved['observations'][0]['observation']
        entry['returns'] = 'bool'
        entry['outcome']['result'] = '0x' + '00' * 32
        self.plan['calls'][0]['expected_return'] = entry['outcome']['result']
        self.assertEqual(self.run_check()['verdict'], 'bound')

    def test_mismatch_takes_precedence_over_missing(self):
        self.saved['observations'].pop()
        self.saved['observations'][0]['observation']['call']['value'] = '0x1'
        self.assertEqual(self.run_check()['verdict'], 'mismatch')

    def test_relay_provenance_is_retained_and_validated(self):
        result = self.run_check()
        self.assertFalse(result['results'][0]['binding']['transport']['independent_provider_verified'])
        self.saved['observations'][0]['observation']['transport']['independent_provider_verified'] = 0
        with self.assertRaises(ValueError):
            self.run_check()

    def test_unknown_fields_are_rejected(self):
        for location in (self.plan, self.saved, self.plan['calls'][0],
                         self.saved['observations'][0], self.plan['calls'][0]['call'],
                         self.saved['observations'][0]['observation']):
            location['gas'] = '0x5208'
            with self.assertRaises(ValueError):
                self.run_check()
            del location['gas']

    def test_invalid_extra_entry_is_validated(self):
        self.saved['observations'].append({'id': 'extra', 'observation': {}})
        with self.assertRaises(ValueError):
            self.run_check()

    def test_nonempty_bounded_sets(self):
        for count in (0, 33):
            self.plan['calls'] = [copy.deepcopy(self.plan['calls'][0]) for _ in range(count)] if count else []
            with self.assertRaisesRegex(ValueError, '1..32'):
                self.run_check()
            self.setUp()

    def test_identifiers(self):
        for bad in ('', 'UPPER', '../outside', 'x' * 49, 3, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                tool.identifier(bad)

    def test_strict_json_and_size(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b' ' * 95001):
            with self.assertRaises(ValueError):
                tool.binding.parse_json(raw)
        self.plan['junk'] = 'x' * 95000
        with self.assertRaisesRegex(ValueError, '95 KB'):
            self.run_check()

    def test_workspace_containment(self):
        with self.assertRaises(ValueError):
            tool.binding.read_json(Path.cwd().parent / 'not-a-workspace-file')

    def test_chain_boolean_and_wrong_chain_rejected(self):
        for chain in (True, 8453):
            self.plan['chain_id'] = chain
            with self.assertRaises(ValueError):
                self.run_check()

    def test_cli_demo_has_no_network(self):
        with patch.object(tool.core.RPC, 'call', side_effect=AssertionError('network forbidden')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(tool.main(['demo']), 0)
            self.assertEqual(json.loads(output.getvalue())['verdict'], 'bound')

    def test_cli_exit_categories(self):
        for outcome in ('bound', 'mismatch', 'inconclusive'):
            with patch.object(tool, 'evaluate', return_value={'verdict': outcome}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(['demo']), {'bound': 0, 'mismatch': 1, 'inconclusive': 2}[outcome])
        with patch.object(tool.binding, 'read_json', side_effect=ValueError('bad evidence')), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(tool.main(['demo']), 2)


if __name__ == '__main__':
    unittest.main()
