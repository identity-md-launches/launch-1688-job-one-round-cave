#!/usr/bin/env python3
"""Check complete evidence for independent Ethereum calls at one reviewed block."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'set_binding', HERE.parent / 'rehearsal-binding' / 'rehearsal_binding.py')
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)
core = binding.core
SCHEMA = 'rehearsal-set-v1'
EVIDENCE_SCHEMA = 'rehearsal-set-evidence-v1'
MAX_ITEMS = 32
LIMITS = (
    'Bound means complete matching historical provider evidence for independent calls '
    'at one exact block. Calls do not share simulated writes: this is not a sequence, '
    'multicall, atomic transaction, or state-effect simulation. Order has no execution '
    'meaning. Expected bytes are supplied by the reviewer; an expected ABI false can '
    'match. No ABI authentication, gas, fees, nonce, authority, current state or future '
    'success is established. Digests identify content, not authenticity. Nothing is sent.'
)


def bounded(value):
    core.require(len(json.dumps(value, allow_nan=False).encode()) <= binding.LIMIT,
                 'input exceeds 95 KB')


def identifier(value):
    core.require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,47}', value),
                 'id must be 1..48 lowercase ASCII letters, digits, underscores or hyphens, starting with a letter')
    return value


def entries(value, keys):
    core.require(isinstance(value, list) and 1 <= len(value) <= MAX_ITEMS,
                 'provide 1..32 entries')
    seen = set()
    for entry in value:
        core.require(isinstance(entry, dict) and set(entry) == keys,
                     'entry must contain exactly the documented fields')
        label = identifier(entry['id'])
        core.require(label not in seen, 'duplicate id: ' + label)
        seen.add(label)
    return value


def plan(value):
    bounded(value)
    core.require(isinstance(value, dict) and
                 set(value) == {'schema', 'chain_id', 'block', 'calls'}, 'invalid set plan fields')
    core.require(value['schema'] == SCHEMA, 'unsupported set plan schema')
    core.require(type(value['chain_id']) is int and value['chain_id'] == 1,
                 'set requires Ethereum mainnet chain_id 1')
    block = binding.exact_block(value['block'])
    calls, seen = [], set()
    for entry in entries(value['calls'], {'id', 'call', 'expected_return'}):
        checked = binding.plan({'schema': binding.SCHEMA, 'chain_id': 1, 'block': block,
                                'call': entry['call'], 'expected_return': entry['expected_return']})
        key = binding.digest(checked['call'])
        core.require(key not in seen, 'duplicate planned call context')
        seen.add(key)
        calls.append({'id': entry['id'], 'call': checked['call'],
                      'expected_return': checked['expected_return']})
    return {'schema': SCHEMA, 'chain_id': 1, 'block': block, 'calls': calls}


def evidence(value):
    bounded(value)
    core.require(isinstance(value, dict) and set(value) == {'schema', 'observations'},
                 'invalid set evidence fields')
    core.require(value['schema'] == EVIDENCE_SCHEMA, 'unsupported set evidence schema')
    items = entries(value['observations'], {'id', 'observation'})
    # Validate even unexpected entries, so malformed evidence is never silently ignored.
    for entry in items:
        binding.observation(entry['observation'])
    return {entry['id']: entry['observation'] for entry in items}


def evaluate(saved, proposed):
    wanted, actual = plan(proposed), evidence(saved)
    ids = {entry['id'] for entry in wanted['calls']}
    missing, extra = sorted(ids - actual.keys()), sorted(actual.keys() - ids)
    results = []
    for entry in wanted['calls']:
        if entry['id'] not in actual:
            continue
        single = {'schema': binding.SCHEMA, 'chain_id': 1, 'block': wanted['block'],
                  'call': entry['call'], 'expected_return': entry['expected_return']}
        checked = binding.bind(actual[entry['id']], single)
        results.append({'id': entry['id'], 'binding': checked})
    verdicts = {entry['binding']['verdict'] for entry in results}
    if extra or 'mismatch' in verdicts:
        verdict, reason = 'mismatch', 'unexpected evidence or at least one call differs from the reviewed plan'
    elif missing or 'inconclusive' in verdicts:
        verdict, reason = 'inconclusive', 'missing evidence or at least one call lacks a conclusive binding'
    else:
        verdict, reason = 'bound', 'every planned independent call matches at the exact reviewed block'
    return {'schema': SCHEMA, 'verdict': verdict, 'reason': reason, 'chain_id': 1,
            'block': wanted['block'], 'planned_count': len(ids), 'observed_count': len(actual),
            'matched_count': sum(entry['binding']['verdict'] == 'bound' for entry in results),
            'missing_ids': missing, 'unexpected_ids': extra, 'results': results,
            'plan_sha256': binding.digest(wanted), 'evidence_sha256': binding.digest(saved),
            'limits': LIMITS}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo', help='check saved real ZTO-first calls offline')
    check = commands.add_parser('check', help='check a reviewed set plan against saved evidence')
    check.add_argument('evidence')
    check.add_argument('plan')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            saved = binding.read_json(HERE / 'zto-set-evidence.json')
            proposed = binding.read_json(HERE / 'zto-set-plan.json')
        else:
            proposed = binding.read_json(args.plan)
            plan(proposed)
            saved = binding.read_json(args.evidence)
        result = evaluate(saved, proposed)
        print(json.dumps(result, indent=2, allow_nan=False))
        return {'bound': 0, 'mismatch': 1, 'inconclusive': 2}[result['verdict']]
    except (ValueError, KeyError, TypeError, OSError, RecursionError, core.RPCError) as exc:
        print(json.dumps({'schema': SCHEMA, 'verdict': 'inconclusive', 'error': str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
