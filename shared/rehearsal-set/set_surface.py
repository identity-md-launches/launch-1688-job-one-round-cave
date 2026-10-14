#!/usr/bin/env python3
"""Join a complete reviewed call set with proof-backed code and flat ABI decoding."""
import argparse
import json
from pathlib import Path
import sys

import rehearsal_set as sets

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'surface-return'))
import surface_call as surface

SCHEMA = 'set-surface-context-v1'
require = sets.core.require
LIMITS = (
    'Independent historical calls, not a stateful sequence or multicall. Signatures '
    'and return layouts are reviewer choices, not authenticated ABI. Selector '
    'patterns do not establish reachability or behavior. Code inclusion is relative '
    'to supplied headers; call returns remain unproven RPC claims. An anchor hash '
    'is an equality check, not authentication. No current-state, authority, gas, '
    'effects, safety, or future-execution guarantee. Nothing is sent.'
)


def evaluate(saved, proposed, choices, proofs, anchor_hash=None):
    """Withhold every decoded member unless the whole set binds and aligns."""
    wanted = sets.plan(proposed)
    planned_ids = {entry['id'] for entry in wanted['calls']}
    require(isinstance(choices, dict) and set(choices) == planned_ids,
            'decoder choices must cover exactly every planned id')
    require(isinstance(proofs, dict) and set(proofs) == planned_ids,
            'proofs must cover exactly every planned id')
    for choice in choices.values():
        require(isinstance(choice, dict) and set(choice) == {'signature', 'return_types'},
                'choice requires exactly signature and return_types')
        surface.argument_types(choice['signature'])
        surface.context.returns.layout(choice['return_types'])
    bound = sets.evaluate(saved, wanted)
    result = {
        'schema': SCHEMA, 'verdict': 'withheld', 'binding_verdict': bound['verdict'],
        'block': wanted['block'], 'planned_count': bound['planned_count'],
        'matched_count': bound['matched_count'], 'missing_ids': bound['missing_ids'],
        'unexpected_ids': bound['unexpected_ids'],
        'binding_reasons': [{'id': item['id'], 'verdict': item['binding']['verdict'],
                            'reason': item['binding']['reason']}
                           for item in bound['results']],
        'input_sha256': {'plan': bound['plan_sha256'], 'evidence': bound['evidence_sha256'],
                         'choices': sets.binding.digest(choices),
                         'proofs': {key: sets.binding.digest(value) for key, value in proofs.items()},
                         'anchor': sets.binding.digest(anchor_hash)},
        'code_checks': [], 'decoded_calls': None, 'limits': LIMITS,
    }
    if bound['verdict'] != 'bound':
        result['reason'] = 'The complete reviewed set did not bind; code joining was not attempted.'
        return result
    actual = sets.evidence(saved)
    contexts = []
    for entry in wanted['calls']:
        label = entry['id']
        choice = choices[label]
        # Binding already validated the modern optional relay provenance. The
        # older flat decoder accepts only the original schema. Project that
        # exact schema, but retain the validated provenance in this join's report
        # and hash the original evidence above; never relabel its source.
        decoder_view = {key: value for key, value in actual[label].items() if key != 'transport'}
        context = surface.evaluate(proofs[label], decoder_view, choice['signature'],
                                   choice['return_types'], anchor_hash)
        contexts.append((label, context))
        result['code_checks'].append({
            'id': label, 'verdict': context['verdict'],
            'failed_checks': context['failed_checks'], 'proof_anchor': context['proof_anchor'],
            'state_inclusion_verified': context['state_inclusion_verified'],
            'source': actual[label]['source'],
            'transport': actual[label].get('transport'),
        })
    if all(context['verdict'] == 'aligned' for _, context in contexts):
        result['verdict'] = 'aligned'
        result['reason'] = 'Every planned call binds and its code, calldata and return context align.'
        result['decoded_calls'] = [{
            'id': label, 'target': context['target'], 'signature': context['signature'],
            'arguments': context['decoded_arguments'], 'returns': context['decoded_values'],
        } for label, context in contexts]
    else:
        result['reason'] = 'At least one code/call context differs; all joined decoded values withheld.'
    sets.bounded(result)
    return result


def demo_inputs():
    # Reuse unmodified historical evidence. Never add a sender to an observation.
    root = HERE.parent / 'surface-return'
    observation = sets.binding.read_json(root / 'zto-pool-balance-call.json')
    label = 'zto-manager-balance'
    saved = {'schema': sets.EVIDENCE_SCHEMA,
             'observations': [{'id': label, 'observation': observation}]}
    proposed = {'schema': sets.SCHEMA, 'chain_id': 1, 'block': dict(observation['block']),
                'calls': [{'id': label, 'call': dict(observation['call']),
                           'expected_return': observation['outcome']['result']}]}
    choices = {label: {'signature': 'balanceOf(address)', 'return_types': ['uint256']}}
    proofs = {label: surface.context.surface.ancestry.read_json(root / 'zto-proof.json')}
    return saved, proposed, choices, proofs


def manifest(value):
    require(isinstance(value, dict) and set(value) == {'schema', 'members'} and
            value['schema'] == 'set-surface-manifest-v1', 'invalid manifest fields/schema')
    members = sets.entries(value['members'], {'id', 'signature', 'return_types', 'proof'})
    choices, proofs = {}, {}
    for item in members:
        require(isinstance(item['proof'], str), 'proof must be a workspace file path')
        label = item['id']
        choices[label] = {key: item[key] for key in ('signature', 'return_types')}
        proofs[label] = surface.context.surface.ancestry.read_json(item['proof'])
    return choices, proofs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--plan')
    parser.add_argument('--evidence')
    parser.add_argument('--manifest')
    parser.add_argument('--anchor-hash', help='independently supplied execution block hash')
    args = parser.parse_args(argv)
    try:
        explicit = (args.plan, args.evidence, args.manifest)
        if args.demo:
            require(not any(explicit) and args.anchor_hash is None,
                    '--demo takes no other options')
            inputs = demo_inputs()
        else:
            require(all(explicit), 'supply --plan, --evidence and --manifest together')
            proposed = sets.binding.read_json(args.plan)
            saved = sets.binding.read_json(args.evidence)
            choices, proofs = manifest(sets.binding.read_json(args.manifest))
            inputs = saved, proposed, choices, proofs
        result = evaluate(*inputs, anchor_hash=args.anchor_hash)
        sets.bounded(result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['verdict'] == 'aligned' else 2
    except (ValueError, KeyError, TypeError, AttributeError, OSError, OverflowError,
            IndexError, RecursionError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'invalid', 'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
