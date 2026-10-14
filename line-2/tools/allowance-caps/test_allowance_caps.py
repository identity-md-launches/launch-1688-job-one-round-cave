"""Real-evidence replay and isolated hypothetical/malformed scenario checks."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

import allowance_caps as tool


class CapTests(unittest.TestCase):
    def setUp(self):
        self.observation = tool.gate.load(tool.exposure.DEFAULT)
        self.caps = tool.gate.load(tool.HERE / 'hypothetical-cap.json')
        self.receipts = tool.gate.load(tool.HERE.parent / 'receipt-exposure/hypothetical-one-zto.json')
        self.owner = self.caps['pairs'][0]['owner']

    def selected(self, result):
        return next(o for o in result['owners'] if o['owner'] == self.owner)

    def test_real_zto_demonstration(self):
        report = tool.assess(self.observation, self.caps, self.receipts)
        row = self.selected(report)
        self.assertEqual(report['measured_pair_count'], 19)
        self.assertEqual(report['changed_pair_count'], 1)
        self.assertEqual(report['block']['block_number'], 26187572)
        self.assertEqual(row['measured_funded_combined_bound_raw'], str(10**18))
        self.assertEqual(row['hypothetical_funded_combined_bound_raw'], str(10**18 // 4))
        self.assertEqual(row['funded_combined_bound_reduction_raw'], str(3 * 10**18 // 4))
        self.assertEqual(row['current_combined_bound_reduction_raw'], '0')

    def test_omitted_pairs_keep_measured_permission(self):
        report = tool.assess(self.observation, self.caps)
        for owner in report['owners']:
            for row in owner['pairs']:
                if not row['explicit_cap']:
                    self.assertEqual(row['measured_allowance_raw'], row['hypothetical_allowance_raw'])
        self.assertEqual(sum(o['remaining_active_measured_pairs'] for o in report['owners']), 3)

    def test_zero_target_models_revocation_only(self):
        self.caps['pairs'][0]['target_allowance_raw'] = '0'
        row = self.selected(tool.assess(self.observation, self.caps, self.receipts))
        self.assertEqual(row['hypothetical_funded_combined_bound_raw'], '0')
        self.assertEqual(row['remaining_active_measured_pairs'], 0)

    def test_unchanged_target(self):
        self.caps['pairs'][0]['target_allowance_raw'] = str(tool.gate.lens.MAX_UINT)
        report = tool.assess(self.observation, self.caps, self.receipts)
        self.assertEqual(report['changed_pair_count'], 0)
        self.assertTrue(all(o['funded_combined_bound_reduction_raw'] == '0' for o in report['owners']))

    def two_pair_case(self):
        # Synthetic mutations remain in tests, never supplied as historical evidence.
        observation = copy.deepcopy(next(o for o in self.observation['observations']
                                         if len(o['raw']['allowances']) >= 2))
        observation['raw']['allowances'] = observation['raw']['allowances'][:2]
        observation['query']['spenders'] = [r['spender'] for r in observation['raw']['allowances']]
        observation['raw']['balances'][0]['result'] = '0x' + format(5, '064x')
        for row in observation['raw']['allowances']:
            row['result'] = '0x' + format(10, '064x')
        specification = copy.deepcopy(self.caps)
        specification['pairs'] = [{'owner': observation['query']['owner'], 'spender': row['spender'],
                                   'target_allowance_raw': '2'} for row in observation['raw']['allowances']]
        return observation, specification

    def test_overlapping_bounds_and_reduction(self):
        observation, caps = self.two_pair_case()
        row = tool.assess(observation, caps)['owners'][0]
        self.assertEqual(len(row['pairs']), 2)
        self.assertEqual(row['measured_current_combined_bound_raw'], '5')
        self.assertEqual(row['hypothetical_current_combined_bound_raw'], '4')
        self.assertEqual(row['current_combined_bound_reduction_raw'], '1')
        self.assertEqual(sum(int(p['funded_bound_reduction_raw']) for p in row['pairs']), 6)

    def test_other_spender_can_preserve_all_exposure(self):
        observation, caps = self.two_pair_case()
        caps['pairs'] = caps['pairs'][:1]
        caps['pairs'][0]['target_allowance_raw'] = '0'
        row = tool.assess(observation, caps)['owners'][0]
        self.assertEqual(row['funded_combined_bound_reduction_raw'], '0')
        self.assertEqual(row['total_capacity_reduction_raw'], '10')

    def test_capacity_sum_above_uint256(self):
        observation, caps = self.two_pair_case()
        maximum = tool.gate.lens.MAX_UINT
        for row in observation['raw']['allowances']:
            row['result'] = '0x' + format(maximum, '064x')
        caps['pairs'] = caps['pairs'][:1]
        caps['pairs'][0]['target_allowance_raw'] = '0'
        row = tool.assess(observation, caps)['owners'][0]
        self.assertEqual(row['total_capacity_reduction_raw'], '0')
        self.assertEqual(row['hypothetical_total_capacity_raw'], str(maximum))

    def test_refuse_increase_unknown_and_duplicate_pair(self):
        observation, caps = self.two_pair_case()
        caps['pairs'][0]['target_allowance_raw'] = '11'
        with self.assertRaisesRegex(ValueError, 'increases'):
            tool.assess(observation, caps)
        caps = copy.deepcopy(self.caps)
        caps['pairs'][0]['owner'] = caps['pairs'][0]['spender']
        with self.assertRaisesRegex(ValueError, 'no measured'):
            tool.assess(self.observation, caps)
        self.caps['pairs'].append(copy.deepcopy(self.caps['pairs'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            tool.assess(self.observation, self.caps)

    def test_strict_schema_and_amounts(self):
        for amount in [True, 0, '-1', '01', '1.0', str(tool.gate.lens.MAX_UINT + 1)]:
            caps = copy.deepcopy(self.caps)
            caps['pairs'][0]['target_allowance_raw'] = amount
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                tool.assess(self.observation, caps)
        for key, value in [('chain_id', True), ('token_address', tool.gate.lens.TOKENS['IMD']),
                           ('pairs', []), ('schema', 'wrong')]:
            caps = copy.deepcopy(self.caps)
            caps[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.assess(self.observation, caps)
        self.caps['pairs'][0]['send'] = True
        with self.assertRaises(ValueError):
            tool.assess(self.observation, self.caps)

    def test_missing_raw_read_and_receipt_overflow(self):
        selected = next(o for o in self.observation['observations'] if o['query']['owner'] == self.owner)
        selected['raw']['allowances'] = []
        with self.assertRaises(ValueError):
            tool.assess(self.observation, self.caps)
        observation, caps = self.two_pair_case()
        receipts = copy.deepcopy(self.receipts)
        receipts['receipts'][0] = {'owner': observation['query']['owner'],
                                   'amount_raw': str(tool.gate.lens.MAX_UINT)}
        with self.assertRaisesRegex(ValueError, 'balance exceeds'):
            tool.assess(observation, caps, receipts)

    def test_immutability_digest_and_order(self):
        original = copy.deepcopy((self.observation, self.caps, self.receipts))
        a = tool.assess(*original)
        reordered = copy.deepcopy(self.observation)
        reordered['observations'].reverse()
        b = tool.assess(reordered, self.caps, self.receipts)
        self.assertEqual(a['owners'], b['owners'])
        self.assertNotEqual(a['input_sha256']['observation'], b['input_sha256']['observation'])
        self.assertEqual(original, (self.observation, self.caps, self.receipts))
        caps = copy.deepcopy(self.caps)
        caps['pairs'][0]['target_allowance_raw'] = '0'
        self.assertNotEqual(a['input_sha256']['caps'], tool.assess(self.observation, caps)['input_sha256']['caps'])

    def test_cli_and_path_guard(self):
        command = [sys.executable, '-B', str(Path(tool.__file__))]
        demo = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertTrue(json.loads(demo.stdout)['demonstration'])
        for args in [['--caps', str(tool.HERE / 'hypothetical-cap.json')],
                     ['--receipts', str(tool.HERE.parent / 'receipt-exposure/hypothetical-one-zto.json')],
                     ['--caps', '../outside.json', '--observation', str(tool.exposure.DEFAULT)]]:
            refused = subprocess.run(command + args, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 1)


if __name__ == '__main__':
    unittest.main()
