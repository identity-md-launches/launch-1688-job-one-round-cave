#!/usr/bin/env python3
"""Proof-backed, conservative legacy-EVM route inventory; not execution simulation."""
import argparse
from collections import deque
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'code-surface'))
import code_surface as surface

ancestry, proof, lens = surface.ancestry, surface.proof, surface.lens
PREVIEW = 16
HALTS = {0x00, 0xf3, 0xfd, 0xfe, 0xff}
INTERESTING = {0x31: 'BALANCE', 0x3b: 'EXTCODESIZE', 0x3c: 'EXTCODECOPY',
               0x3f: 'EXTCODEHASH', 0x54: 'SLOAD', 0x55: 'SSTORE',
               0x5c: 'TLOAD', 0x5d: 'TSTORE', 0xf0: 'CREATE', 0xf1: 'CALL',
               0xf2: 'CALLCODE', 0xf4: 'DELEGATECALL', 0xf5: 'CREATE2',
               0xfa: 'STATICCALL', 0xff: 'SELFDESTRUCT'}


def graph(code):
    """Decode all bytes; unknown jump targets use one shared destination set.

    Only an immediately preceding PUSH0..PUSH32 determines a jump target.
    No alternative instruction can jump directly onto that JUMP/JUMPI, since
    it is not JUMPDEST. Both JUMPI outcomes remain possible. All other bytes
    except the explicit halts fall through, even undefined opcodes; this
    deliberately over-approximates exceptional halting. Metadata is not removed.
    """
    lens.require(isinstance(code, bytes) and 0 < len(code) <= lens.MAX_CODE,
                 'runtime must contain 1 to 24576 bytes')
    lens.require(code[0] != 0xef, '0xef-prefixed code requires a different execution model')
    decoded = surface.instructions(code)
    by_pc = {item[0]: item for item in decoded}
    destinations = {pc for pc, op, _, _ in decoded if op == 0x5b}
    edges, jumps, dynamic = {}, [], set()
    for index, (pc, op, _, _) in enumerate(decoded):
        following = decoded[index + 1][0] if index + 1 < len(decoded) else None
        edges[pc] = []
        if op not in HALTS and op != 0x56 and following is not None:
            edges[pc].append(following)
        if op not in (0x56, 0x57):
            continue
        previous = decoded[index - 1] if index else None
        target = None
        if previous and 0x5f <= previous[1] <= 0x7f and previous[3]:
            target = int.from_bytes(previous[2], 'big')
        valid = target in destinations if target is not None else None
        if target is None:
            dynamic.add(pc)
        elif valid:
            edges[pc].append(target)
        jumps.append({'pc': pc, 'opcode': 'JUMP' if op == 0x56 else 'JUMPI',
                      'target_kind': 'dynamic' if target is None else 'adjacent-push',
                      'constant_target_pc': target, 'valid_jumpdest': valid,
                      'fallthrough_pc': following if op == 0x57 else None})
    return decoded, by_pc, destinations, edges, jumps, dynamic


def walk(edges, dynamic, destinations, expand_dynamic):
    """Linear graph walk: expand the shared all-JUMPDEST set at most once."""
    pending, visited, expanded = deque([0]), set(), False
    while pending:
        pc = pending.popleft()
        if pc in visited:
            continue
        visited.add(pc)
        pending.extend(edges[pc])
        if expand_dynamic and pc in dynamic and not expanded:
            pending.extend(sorted(destinations))
            expanded = True
    return visited, expanded


def scan(code, requested_pcs=()):
    requested_pcs = list(requested_pcs)
    lens.require(len(requested_pcs) <= 32 and len(set(requested_pcs)) == len(requested_pcs)
                 and all(type(pc) is int and 0 <= pc < lens.MAX_CODE for pc in requested_pcs),
                 'query PCs must be up to 32 distinct integers from 0 to 24575')
    decoded, by_pc, destinations, edges, jumps, dynamic = graph(code)
    direct, _ = walk(edges, dynamic, destinations, False)
    conservative, expanded = walk(edges, dynamic, destinations, True)
    metadata = surface.opcodes.solidity_metadata(code)

    def status(pc):
        if pc >= len(code):
            return 'outside-runtime'
        if pc not in by_pc:
            return 'push-operand-byte'
        if pc in direct:
            return 'direct-model-path'
        if pc in conservative:
            return 'dynamic-target-candidate'
        return 'excluded-by-model'

    def annotation(pc):
        return {'pc': pc, 'route_status': status(pc),
                'in_recognized_metadata': bool(metadata and pc >= metadata['start'])}

    counts = {name: 0 for name in ('direct-model-path', 'dynamic-target-candidate', 'excluded-by-model')}
    operations, operation_counts = [], {}
    for pc, op, _, _ in decoded:
        counts[status(pc)] += 1
        if op in INTERESTING:
            name = INTERESTING[op]
            group = operation_counts.setdefault(name, {key: 0 for key in counts})
            group[status(pc)] += 1
            operations.append({'opcode': name, **annotation(pc)})
    for jump in jumps:
        jump.update(annotation(jump['pc']))
    _, selectors, _ = surface.scan(code)
    return {
        'model': 'legacy-evm-adjacent-push-v1', 'entry_pc': 0,
        'runtime_bytes': len(code), 'instruction_count': len(decoded),
        'recognized_solidity_metadata': metadata,
        'instruction_route_counts': counts, 'jumpdest_count': len(destinations),
        'jump_count': len(jumps), 'dynamic_jump_count': len(dynamic),
        'dynamic_jump_expansion_used': expanded,
        'direct_model_dynamic_jump_count': len(dynamic & direct),
        'conservative_model_dynamic_jump_count': len(dynamic & conservative),
        'invalid_constant_jump_count': sum(jump['valid_jumpdest'] is False for jump in jumps),
        'jump_preview': jumps[:PREVIEW], 'omitted_jump_count': max(0, len(jumps) - PREVIEW),
        'operation_counts': operation_counts, 'operation_preview': operations[:PREVIEW],
        'omitted_operation_count': max(0, len(operations) - PREVIEW),
        'selector_pattern_count': len(selectors),
        'selector_pattern_preview': [{**item, 'jump_route_status': status(item['jumpi_pc']),
                                      'destination_route_status': status(item['destination_pc'])}
                                     for item in selectors[:PREVIEW]],
        'omitted_selector_pattern_count': max(0, len(selectors) - PREVIEW),
        'queried_pcs': [annotation(pc) for pc in requested_pcs],
        'truncated_push_count': sum(not complete for _, _, _, complete in decoded),
    }


def inspect(bundle, anchor_hash=None, requested_pcs=()):
    checked = proof.verify(bundle, anchor_hash)
    observation = bundle['observation']
    runtimes, seen = [], {}
    for node in observation['nodes']:
        for item, role in ((node, 'candidate-path'), (node.get('beacon'), 'beacon')):
            if item is None:
                continue
            address = lens.address(item['address'])
            if address in seen:
                if role not in seen[address]['roles']:
                    seen[address]['roles'].append(role)
                continue
            runtime = {'address': address, 'code_hash': lens.fixed_hex(item['code_hash'], 32),
                       'roles': [role], **scan(lens.code_bytes(item['code']), requested_pcs)}
            seen[address] = runtime
            runtimes.append(runtime)
    return {
        'schema': 'code-routes-result-v1', 'chain_id': 1, 'target': checked['target'],
        'code_block': ancestry.block_identity(observation['block']),
        'proof': checked, 'runtimes': runtimes,
        'anchor_authenticity_verified': False, 'execution_reachability_verified': False,
        'semantic_safety_verified': False,
        'scope': 'Structural routes in full proof-backed historical runtime, under the named legacy model. '
                 'Direct paths can be infeasible: stack, conditions, gas and call context are not evaluated. '
                 'Every encountered dynamic jump conservatively admits every decoded JUMPDEST. '
                 'Excluded-by-model is not a safety finding. Unknown non-control opcodes fall through; '
                 'future control-flow opcodes, EOF and 0xef-prefixed delegation indicators are unsupported. '
                 'Each runtime is analyzed separately from PC 0, not as a proven inter-contract route. '
                 'Metadata is annotated, never removed. No current state, ABI, source equivalence, '
                 'external code behavior, consensus, finality, anchor authenticity or safety is verified.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, help='workspace-local raw Code Proof bundle')
    parser.add_argument('--anchor-hash', help='independently trusted execution block hash')
    parser.add_argument('--pc', type=lambda value: int(value, 0), action='append', default=[],
                        help='query decimal or 0x-prefixed byte offset; repeat up to 32 times')
    args = parser.parse_args()
    try:
        result = inspect(ancestry.read_json(args.bundle), args.anchor_hash, args.pc)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError, AttributeError,
            IndexError, RecursionError) as error:
        print('Code Routes: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
