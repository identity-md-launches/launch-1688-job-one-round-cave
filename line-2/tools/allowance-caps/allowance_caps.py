#!/usr/bin/env python3
"""Compare explicit hypothetical allowance reductions against measured ERC-20 evidence."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'receipt-exposure'))
import receipt_exposure as exposure

gate = exposure.gate
SCHEMA = 'permission-hypothetical-caps-v1'


def parse_caps(value, measured):
    gate.exact_keys(value, ('schema', 'chain_id', 'token_address', 'pairs'), 'caps')
    gate.lens.require(value['schema'] == SCHEMA, 'unsupported caps schema')
    gate.lens.require(type(value['chain_id']) is int and value['chain_id'] == 1,
                      'caps must select Ethereum chain 1')
    gate.lens.require(gate.lens.address(value['token_address']) == measured['token_address'],
                      'caps token differs from observation')
    entries = value['pairs']
    gate.lens.require(isinstance(entries, list) and 1 <= len(entries) <= gate.lens.MAX_PAIRS,
                      'caps must contain 1..64 explicit pairs')
    caps = {}
    for entry in entries:
        gate.exact_keys(entry, ('owner', 'spender', 'target_allowance_raw'), 'cap pair')
        pair = (gate.lens.address(entry['owner']), gate.lens.address(entry['spender']))
        gate.lens.require(pair not in caps, 'duplicate cap pair')
        gate.lens.require(pair in measured['pairs'], 'cap pair has no measured permission evidence')
        target = gate.raw_uint(entry['target_allowance_raw'])
        gate.lens.require(target <= int(measured['pairs'][pair]['allowance_raw']),
                          'target allowance increases measured permission')
        caps[pair] = target
    return caps


def assess(observation, specification, receipts=None):
    # Revalidate raw ABI reads; a previously computed report is never evidence.
    baseline = exposure.assess(observation, receipts)
    measured = gate.changes.flatten(observation)
    caps = parse_caps(specification, measured)
    owners = []
    for owner in baseline['owners']:
        address = owner['owner']
        balance, funded = int(owner['balance_raw']), int(owner['hypothetical_balance_raw'])
        rows = []
        old_sum = new_sum = 0
        for row in owner['pairs']:
            pair = (address, row['spender'])
            old = int(row['allowance_raw'])
            target = caps.get(pair, old)
            old_sum += old
            new_sum += target
            rows.append({
                'spender': row['spender'], 'explicit_cap': pair in caps,
                'measured_allowance_raw': str(old), 'hypothetical_allowance_raw': str(target),
                'allowance_reduction_raw': str(old - target),
                'measured_funded_bound_raw': str(min(funded, old)),
                'hypothetical_funded_bound_raw': str(min(funded, target)),
                'funded_bound_reduction_raw': str(min(funded, old) - min(funded, target)),
            })
        owners.append({
            'owner': address, 'balance_raw': str(balance),
            'hypothetical_receipt_raw': owner['hypothetical_receipt_raw'],
            'receipt_explicitly_supplied': owner['receipt_explicitly_supplied'],
            'hypothetical_balance_raw': str(funded),
            'measured_current_combined_bound_raw': str(min(balance, old_sum)),
            'hypothetical_current_combined_bound_raw': str(min(balance, new_sum)),
            'current_combined_bound_reduction_raw': str(min(balance, old_sum) - min(balance, new_sum)),
            'measured_funded_combined_bound_raw': str(min(funded, old_sum)),
            'hypothetical_funded_combined_bound_raw': str(min(funded, new_sum)),
            'funded_combined_bound_reduction_raw': str(min(funded, old_sum) - min(funded, new_sum)),
            'measured_total_capacity_raw': str(min(gate.lens.MAX_UINT, old_sum)),
            'hypothetical_total_capacity_raw': str(min(gate.lens.MAX_UINT, new_sum)),
            'total_capacity_reduction_raw': str(min(gate.lens.MAX_UINT, old_sum)
                                                - min(gate.lens.MAX_UINT, new_sum)),
            'remaining_active_measured_pairs': sum(int(r['hypothetical_allowance_raw']) > 0 for r in rows),
            'pairs': rows,
        })
    return {
        'schema': 'permission-cap-comparison-v1', 'mode': 'hypothetical_allowance_reductions',
        'chain_id': measured['chain_id'], 'token': measured['token'],
        'token_address': measured['token_address'], 'decimals': measured['decimals'],
        'block': baseline['block'], 'complete_wallet_audit': False,
        'measured_pair_count': len(measured['pairs']), 'explicit_cap_count': len(caps),
        'changed_pair_count': sum(caps[p] < int(measured['pairs'][p]['allowance_raw']) for p in caps),
        'input_sha256': {**baseline['input_sha256'], 'caps': exposure.digest(specification)},
        'owners': owners,
        'limitations': [
            'Hypothetical comparison only: no permission is changed and no transaction is produced.',
            'Unlisted measured pairs retain their full measured allowance, never default to zero.',
            'Allowance reductions and optional net receipts are explicit caller-selected scenarios.',
            'Combined bounds cap the sum of overlapping allowances at owner balance; pair bounds must not be summed.',
            'Total capacity caps allowance sums at uint256 maximum, independent of current balance.',
            'Historical trusted RPC evidence, not state proofs, current state or future execution.',
            'No proof of enforceable caps, token semantics, safe approval sequencing or spender trust.',
            'Unknown permissions, Permit2, signatures and custom authorizations remain outside coverage.',
            'Zero measured exposure does not establish wallet safety; owner review is still required.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', help='workspace raw permission evidence; requires --caps')
    parser.add_argument('--caps', help='workspace explicit hypothetical allowance reductions; requires --observation')
    parser.add_argument('--receipts', help='optional workspace hypothetical net receipt scenario')
    args = parser.parse_args(argv)
    try:
        demo = args.observation is None and args.caps is None
        gate.lens.require((args.observation is None) == (args.caps is None),
                          'provide both --observation and --caps, or neither for the demonstration')
        gate.lens.require(not demo or args.receipts is None,
                          'custom receipts require explicit --observation and --caps')
        result = assess(gate.load(args.observation or exposure.DEFAULT),
                        gate.load(args.caps or HERE / 'hypothetical-cap.json'),
                        gate.load(HERE.parent / 'receipt-exposure/hypothetical-one-zto.json') if demo
                        else (None if args.receipts is None else gate.load(args.receipts)))
        result['demonstration'] = demo
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
