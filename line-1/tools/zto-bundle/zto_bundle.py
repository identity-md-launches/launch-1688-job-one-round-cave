#!/usr/bin/env python3
"""Carry and recheck one ZTO/IMD planning bound with its three source documents."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'zto-handoff'))
import zto_handoff as h

SCHEMA = 'zto-evidence-bundle-v1'
KEYS = {'schema', 'snapshot', 'report', 'policy', 'handoff', 'bundle_sha256'}
require = h.review.sizes.path.z.require


def bounded_copy(value):
    """Bound total serialized size and forbid ambiguous JSON numbers."""
    encoded = h.review.canonical(value)
    require(len(encoded.encode('ascii')) <= 100000, 'bundle exceeds 100 KB')
    return json.loads(encoded, object_pairs_hook=h.review.pairs,
                      parse_float=h.review.unsupported_number,
                      parse_constant=h.review.unsupported_number)


def pack(snapshot, report, policy, amount, mode='caller_policy'):
    value = bounded_copy({
        'schema': SCHEMA, 'snapshot': snapshot, 'report': report,
        'policy': policy,
        'handoff': h.handoff(snapshot, report, policy, amount, mode),
    })
    value['bundle_sha256'] = h.review.digest(value)
    verify(value, policy)
    return value


def verify(value, expected_policy):
    """Recompute evidence only under the receiver's separately supplied policy.

    A self-digest is not authenticity. Even a fully re-digested replacement
    bundle cannot silently change the receiver's block/age/amount/tolerance
    policy. The receiver still trusts its own policy and the supplied state.
    """
    value = bounded_copy(value)
    require(type(value) is dict and set(value) == KEYS,
            'bundle must contain exactly the documented fields')
    require(value['schema'] == SCHEMA, 'wrong bundle schema')
    unsigned = {key: item for key, item in value.items() if key != 'bundle_sha256'}
    require(value['bundle_sha256'] == h.review.digest(unsigned), 'bundle digest mismatch')
    require(h.review.canonical(value['policy']) == h.review.canonical(expected_policy),
            'bundled policy differs from receiver policy')
    checked = h.verify_evidence(value['handoff'], value['snapshot'],
                                value['report'], expected_policy)
    rebuilt = h.handoff(value['snapshot'], value['report'], expected_policy,
                        value['handoff']['requested_input'], value['handoff']['mode'])
    require(not h.review.differences(value['handoff'], rebuilt),
            'handoff types or values differ from recomputed evidence')
    return {
        'schema': 'zto-evidence-bundle-verification-v1', 'status': checked['status'],
        'bundle_sha256': value['bundle_sha256'],
        'handoff_sha256': checked['handoff_sha256'],
        'pool_id': checked['pool_id'], 'block': value['handoff']['block'],
        'input_token': checked['input_token'], 'output_token': checked['output_token'],
        'requested_input': value['handoff']['requested_input'],
        'minimum_output': value['handoff']['minimum_output'],
        'limitations': [
            'Receiver policy is a separate trust input; the demo policy is historical only.',
            'Digests bind supplied files, not Ethereum consensus or provider authenticity.',
            'Reuses the existing pool arithmetic; no independent numerical implementation.',
            'No current quote, execution approval, settlement or transaction is provided.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true', help='offline real historical evidence')
    mode.add_argument('--pack', action='store_true', help='pack caller-supplied evidence')
    mode.add_argument('--verify', metavar='BUNDLE', help='verify a received workspace bundle')
    parser.add_argument('--policy', help='separate caller/receiver policy workspace JSON')
    parser.add_argument('--snapshot', help='workspace ZTO Path snapshot JSON')
    parser.add_argument('--report', help='workspace ZTO Sizes report JSON')
    parser.add_argument('--amount', help='one exact reviewed decimal input amount')
    parser.add_argument('--save', help='workspace destination for a new bundle')
    args = parser.parse_args(argv)
    try:
        if args.verify:
            require(args.policy is not None, '--verify requires a separate receiver --policy')
            require(not any((args.snapshot, args.report, args.amount, args.save)),
                    '--verify cannot pack or save evidence')
            result = verify(h.review.read_json(args.verify), h.review.read_json(args.policy))
        else:
            if args.demo:
                require(not any((args.policy, args.snapshot, args.report, args.amount)),
                        '--demo cannot be combined with caller evidence')
                snapshot = h.review.read_json(h.review.DEFAULT_SNAPSHOT)
                report = h.review.read_json(h.review.DEFAULT_REPORT)
                policy = h.review.read_json(h.review.HERE / 'demo-policy.json')
                amount, selected_mode = '100000000', 'historical_demo'
            else:
                require(all((args.policy, args.snapshot, args.report, args.amount, args.save)),
                        '--pack requires --policy, --snapshot, --report, --amount and --save')
                snapshot, report, policy = [h.review.read_json(p) for p in
                                            (args.snapshot, args.report, args.policy)]
                amount, selected_mode = args.amount, 'caller_policy'
            bundle = pack(snapshot, report, policy, amount, selected_mode)
            result = verify(bundle, policy)
            if args.save:
                h.review.sizes.path.save_json(args.save, bundle)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError,
            RecursionError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
