"""Real proof replays, synthetic control-flow cases and an independent graph oracle."""
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
import code_routes as routes

FOLDER = Path(__file__).resolve().parent


def evidence(token='zto'):
    return routes.ancestry.read_json(FOLDER / (token + '-proof.json'))


def query(code, *pcs):
    return {entry['pc']: entry['route_status'] for entry in routes.scan(code, pcs)['queried_pcs']}


class RoutesTests(unittest.TestCase):
    def test_real_proofs(self):
        for token, expected in (('zto', (61, 16)), ('imd', (1324, 311))):
            result = routes.inspect(evidence(token))
            runtime = result['runtimes'][0]
            self.assertEqual((runtime['jump_count'], runtime['dynamic_jump_count']), expected)
            self.assertTrue(result['proof']['state_inclusion_verified'])
            self.assertEqual(result['proof']['anchor'], 'unanchored-rpc-header')
            self.assertFalse(result['anchor_authenticity_verified'])
            self.assertFalse(result['execution_reachability_verified'])
            self.assertFalse(result['semantic_safety_verified'])
            self.assertTrue(runtime['dynamic_jump_expansion_used'])
            self.assertEqual(sum(runtime['instruction_route_counts'].values()), runtime['instruction_count'])

    def test_constant_jump_skips_unreachable_call(self):
        result = routes.scan(bytes.fromhex('600456f15b00'), [3, 4])
        self.assertEqual(result['queried_pcs'][0]['route_status'], 'excluded-by-model')
        self.assertEqual(result['queried_pcs'][1]['route_status'], 'direct-model-path')
        self.assertEqual(result['jump_preview'][0]['constant_target_pc'], 4)
        self.assertTrue(result['jump_preview'][0]['valid_jumpdest'])

    def test_conditional_keeps_both_outcomes_even_constant_condition(self):
        code = bytes.fromhex('5f600657f1005bf400')
        statuses = query(code, 4, 7)
        self.assertEqual(set(statuses.values()), {'direct-model-path'})

    def test_jumpdest_inside_push_is_invalid(self):
        result = routes.scan(bytes.fromhex('600456605b00'))
        self.assertEqual(result['jumpdest_count'], 0)
        self.assertEqual(result['invalid_constant_jump_count'], 1)
        self.assertEqual(query(bytes.fromhex('600456605b00'), 4)[4], 'push-operand-byte')

    def test_invalid_unconditional_jump_has_no_fallthrough(self):
        code = bytes.fromhex('60ff56f15b00')
        self.assertEqual(query(code, 3, 4), {3: 'excluded-by-model', 4: 'excluded-by-model'})

    def test_invalid_conditional_still_has_fallthrough(self):
        self.assertEqual(query(bytes.fromhex('60ff57f100'), 3)[3], 'direct-model-path')

    def test_dynamic_jump_admits_all_destinations_but_no_fallthrough(self):
        code = bytes.fromhex('3556f15bf4005bfa00')
        self.assertEqual(query(code, 2, 4, 7), {2: 'excluded-by-model',
                         4: 'dynamic-target-candidate', 7: 'dynamic-target-candidate'})
        self.assertTrue(routes.scan(code)['dynamic_jump_expansion_used'])

    def test_dynamic_conditional_keeps_fallthrough(self):
        code = bytes.fromhex('3557f1005bfa00')
        self.assertEqual(query(code, 2, 5), {2: 'direct-model-path', 5: 'dynamic-target-candidate'})

    def test_unreachable_dynamic_jump_does_not_open_routes(self):
        code = bytes.fromhex('00565bf400')
        result = routes.scan(code)
        self.assertEqual(result['dynamic_jump_count'], 1)
        self.assertFalse(result['dynamic_jump_expansion_used'])
        self.assertEqual(query(code, 3)[3], 'excluded-by-model')

    def test_push0_target_and_self_loop_terminate(self):
        code = bytes.fromhex('5b5f56f4')
        result = routes.scan(code)
        self.assertEqual(result['jump_preview'][0]['constant_target_pc'], 0)
        self.assertTrue(result['jump_preview'][0]['valid_jumpdest'])
        self.assertEqual(query(code, 3)[3], 'excluded-by-model')

    def test_previous_push_does_not_cross_jumpdest(self):
        result = routes.scan(bytes.fromhex('60035b56'))
        self.assertEqual(result['jump_preview'][0]['target_kind'], 'dynamic')

    def test_halting_operations_and_unknown_opcode(self):
        for opcode in routes.HALTS:
            self.assertEqual(query(bytes([opcode, 0xf4]), 1)[1], 'excluded-by-model')
        # Undefined bytes are intentionally allowed to fall through: no fork claim.
        self.assertEqual(query(bytes.fromhex('0cf400'), 1)[1], 'direct-model-path')

    def test_no_control_flow_from_push_operand(self):
        result = routes.scan(bytes.fromhex('635b5657f400'))
        self.assertEqual(result['jump_count'], 0)
        self.assertEqual(result['jumpdest_count'], 0)
        self.assertEqual(result['operation_counts'], {})

    def test_truncated_push_takes_remaining_bytes_as_operand(self):
        result = routes.scan(bytes.fromhex('7f5bf456'), [0, 1, 3, 4])
        self.assertEqual(result['instruction_count'], 1)
        self.assertEqual(result['truncated_push_count'], 1)
        self.assertEqual(result['jump_count'], 0)
        self.assertEqual([p['route_status'] for p in result['queried_pcs']],
                         ['direct-model-path', 'push-operand-byte', 'push-operand-byte', 'outside-runtime'])

    def test_metadata_is_not_discarded(self):
        # CBOR bytes contain a decoded destination followed by DELEGATECALL.
        metadata = bytes.fromhex('a264736f6c634300081a6469706673425bf4')
        code = b'\x35\x56' + metadata + len(metadata).to_bytes(2, 'big')
        result = routes.scan(code)
        self.assertIsNotNone(result['recognized_solidity_metadata'])
        hit = next(op for op in result['operation_preview'] if op['opcode'] == 'DELEGATECALL')
        self.assertTrue(hit['in_recognized_metadata'])
        self.assertEqual(hit['route_status'], 'dynamic-target-candidate')

    def test_eof_and_delegation_indicators_refused(self):
        for code in (bytes.fromhex('ef00'), bytes.fromhex('ef0100' + routes.lens.ZTO[2:])):
            with self.assertRaisesRegex(ValueError, 'different execution model'):
                routes.scan(code)

    def test_input_and_query_bounds(self):
        for code in (b'', b'\0' * (routes.lens.MAX_CODE + 1), '6000'):
            with self.assertRaises(ValueError):
                routes.scan(code)
        for pcs in ([-1], [True], [0, 0], [24576], list(range(33))):
            with self.assertRaises(ValueError):
                routes.scan(b'\0', pcs)

    def test_dense_dynamic_graph_is_bounded(self):
        result = routes.scan(b'\x5b\x56' * (routes.lens.MAX_CODE // 2))
        self.assertEqual(result['jump_count'], 12288)
        self.assertEqual(result['instruction_route_counts']['dynamic-target-candidate'], 24574)
        self.assertEqual(len(result['jump_preview']), routes.PREVIEW)
        self.assertLess(len(json.dumps(result, indent=2)), 20000)

    def test_compare_against_explicit_graph_oracle(self):
        # Separate decoder and exhaustive materialized graph for small byte streams.
        rng = random.Random(32)
        for _ in range(250):
            code = bytes(rng.choice([0, 0x14, 0x35, 0x56, 0x57, 0x5b, 0x5f,
                                     0x60, 0x61, 0x80, 0xf1, 0xf3, 0xfe])
                         for _ in range(rng.randrange(1, 100)))
            decoded, pc = [], 0
            while pc < len(code):
                decoded.append(pc)
                pc += 1 + (code[pc] - 95 if 96 <= code[pc] <= 127 else 0)
            destinations = {pc for pc in decoded if code[pc] == 0x5b}
            edges = {}
            for index, pc in enumerate(decoded):
                opcode = code[pc]
                successors = set()
                if opcode not in (0, 0x56, 0xf3, 0xfd, 0xfe, 0xff) and index + 1 < len(decoded):
                    successors.add(decoded[index + 1])
                if opcode in (0x56, 0x57):
                    previous = decoded[index - 1] if index else None
                    if previous is not None and 95 <= code[previous] <= 127:
                        target = int.from_bytes(code[previous + 1:pc], 'big')
                        if target in destinations:
                            successors.add(target)
                    else:
                        successors |= destinations
                edges[pc] = successors
            reached = {0}
            while True:
                extended = reached | set().union(*(edges[pc] for pc in reached))
                if extended == reached:
                    break
                reached = extended
            production = routes.graph(code)
            actual, _ = routes.walk(production[3], production[5], production[2], True)
            self.assertEqual(actual, reached)

    def test_corrupt_proofs_refused_before_scan(self):
        for mutation in ('header', 'proof', 'runtime'):
            bundle = evidence()
            if mutation == 'header':
                bundle['header_rlp'] = bundle['header_rlp'][:-2] + 'ff'
            elif mutation == 'proof':
                bundle['proofs'][0]['accountProof'].pop()
            else:
                node = bundle['observation']['nodes'][0]
                code = bytes.fromhex('5b5f56')
                node.update(code='0x' + code.hex(), code_bytes=len(code), code_hash=routes.lens.digest(code))
                bundle['observation']['effective_code_hash'] = node['code_hash']
                bundle['proofs'][0]['codeHash'] = node['code_hash']
            with self.assertRaises(ValueError):
                routes.inspect(bundle)

    def test_anchor_match_is_not_authenticity(self):
        bundle = evidence()
        result = routes.inspect(bundle, bundle['observation']['block']['hash'])
        self.assertFalse(result['anchor_authenticity_verified'])
        self.assertEqual(result['proof']['anchor'], 'caller-supplied-block-hash')
        old = routes.ancestry.read_json(FOLDER.parent / 'code-proof/zto-proof.json')
        with self.assertRaises(ValueError):
            routes.inspect(bundle, old['observation']['block']['hash'])

    def test_beacon_dedup_preserves_unproven_warning(self):
        spec = importlib.util.spec_from_file_location('proof_fixture', FOLDER.parent / 'code-proof/test_code_proof.py')
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        result = routes.inspect(fixture.synthetic_beacon_bundle())
        self.assertEqual(len(result['runtimes']), 2)
        runtime = next(r for r in result['runtimes'] if r['address'] == routes.lens.IMD)
        self.assertEqual(set(runtime['roles']), {'beacon', 'candidate-path'})
        self.assertEqual(result['proof']['unproven_beacon_call_results'], [routes.lens.IMD])

    def test_json_boundaries(self):
        with self.assertRaises(ValueError):
            json.loads('{"x":1,"x":2}', object_pairs_hook=routes.ancestry.no_duplicates)
        with self.assertRaises(ValueError):
            routes.ancestry.read_json(Path.cwd().parent / 'outside.json')

    def test_cli_success_and_failure_without_partial_output(self):
        command = [sys.executable, '-B', str(FOLDER / 'code_routes.py'), '--bundle',
                   str(FOLDER.parent / 'code-delta/zto-later-proof.json')]
        success = subprocess.run(command + ['--pc', '0x0'], capture_output=True, text=True, timeout=30)
        self.assertEqual(success.returncode, 0, success.stderr)
        result = json.loads(success.stdout)
        self.assertEqual(result['runtimes'][0]['queried_pcs'][0]['route_status'], 'direct-model-path')
        failure = subprocess.run(command + ['--pc', '-1'], capture_output=True, text=True, timeout=30)
        self.assertEqual(failure.returncode, 1)
        self.assertEqual(failure.stdout, '')

    def test_demo(self):
        import demo
        self.assertTrue(demo.main()['demonstration_passed'])


if __name__ == '__main__':
    unittest.main()
