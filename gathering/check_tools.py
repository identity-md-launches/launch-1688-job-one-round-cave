#!/usr/bin/env python3
"""Run all line checks and offline demonstrations without editing line files."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def checks():
    commands = []
    for number in range(1, 5):
        for folder in sorted(Path(f'line-{number}/tools').iterdir()):
            if list(folder.glob('test_*.py')):
                commands.append((f'line-{number}-{folder.name}-suite',
                    ['-m', 'unittest', 'discover', '-s', str(folder), '-p', 'test_*.py', '-v'], 0))
    commands.extend([
        ('shared-rehearsal-set-demo', ['shared/rehearsal-set/rehearsal_set.py', 'demo'], 0),
        ('set-surface-demo', ['shared/rehearsal-set/set_surface.py', '--demo'], 0),
        ('zto-bundle-demo', ['line-1/tools/zto-bundle/zto_bundle.py', '--demo'], 0),
        ('receipt-exposure-demo', ['line-2/tools/receipt-exposure/receipt_exposure.py'], 0),
        ('allowance-caps-demo', ['line-2/tools/allowance-caps/allowance_caps.py'], 0),
        ('code-metadata-demo', ['line-3/tools/code-metadata/demo.py'], 0),
        ('code-routes-demo', ['line-3/tools/code-routes/demo.py'], 0),
        ('rehearsal-binding-demo', ['line-4/tools/rehearsal-binding/rehearsal_binding.py', 'demo'], 0),
        ('rehearsal-set-demo', ['line-4/tools/rehearsal-set/rehearsal_set.py', 'demo'], 0),
        ('surface-call-demo', ['shared/surface-return/surface_call.py', '--demo'], 0),
        ('bundle-refresh-demo', ['line-2/tools/bundle-refresh/bundle_refresh.py'], 0),
        ('code-constants-demo', ['line-3/tools/code-constants/demo.py'], 0),
        ('calldata-lens-demo', ['line-4/tools/calldata-lens/calldata_lens.py', 'demo'], 0),
        ('zto-handoff-evidence', ['line-1/tools/zto-handoff/zto_handoff.py', '--demo', '--verify-evidence', 'line-1/tools/zto-handoff/demo-handoff.json'], 0),
        ('surface-return-demo', ['shared/surface-return/surface_return.py', '--demo'], 0),
        ('surface-return-block-mismatch', ['shared/surface-return/surface_return.py', '--bundle', 'shared/surface-return/zto-proof.json', '--observation', 'shared/surface-return/zto-other-block-call.json', '--signature', 'totalSupply()', '--types', 'uint256'], 2),
        ('return-lens-demo', ['line-4/tools/return-lens/return_lens.py', 'demo'], 0),
        ('code-surface-demo', ['line-3/tools/code-surface/demo.py'], 0),
        ('code-delta-demo', ['line-3/tools/code-delta/demo.py'], 0),
        ('draft-bundle-demo', ['line-2/tools/draft-bundle/draft_bundle.py'], 0),
        ('draft-age-demo', ['line-2/tools/draft-age/draft_age.py'], 0),
        ('rehearsal-expiry-demo', ['line-4/tools/rehearsal-expiry/rehearsal_expiry.py', 'demo'], 0),
        ('zto-handoff-demo', ['line-1/tools/zto-handoff/zto_handoff.py', '--demo', '--amount', '100000000'], 0),
        ('zto-handoff-verify', ['line-1/tools/zto-handoff/zto_handoff.py', '--verify', 'line-1/tools/zto-handoff/demo-handoff.json'], 0),
        ('permission-revert-context-demo', ['shared/permission-revert-context/permission_revert_context.py'], 0),
        ('zto-refresh-demo', ['line-1/tools/zto-refresh/zto_refresh.py'], 0),
        ('zto-review-demo', ['line-1/tools/zto-review/zto_review.py', '--demo'], 0),
        ('draft-witness-demo', ['line-2/tools/draft-witness/draft_witness.py'], 0),
        ('draft-refresh-demo', ['line-2/tools/draft-refresh/draft_refresh.py'], 0),
        ('code-review-demo', ['line-3/tools/code-review/demo.py'], 0),
        ('code-set-demo', ['line-3/tools/code-set/code_set_demo.py'], 0),
        ('relay-rehearsal-demo', ['line-4/tools/relay-rehearsal/relay_rehearsal.py', 'demo'], 0),
        ('revert-expectation-demo', ['line-4/tools/revert-expectation/revert_expectation.py', 'demo'], 0),
        ('zto-archive-demo', ['line-1/tools/zto-archive/zto_archive.py', '--snapshot', 'line-1/tools/zto-path/observation.json'], 0),
        ('zto-capacity-demo', ['line-1/tools/zto-capacity/zto_capacity.py', '--ceiling', '1000000000', '--slippage-bps', '100'], 0),
        ('allowance-union-demo', ['line-2/tools/allowance-union/allowance_union.py'], 0),
        ('approval-draft-demo', ['line-2/tools/approval-draft/approval_draft.py'], 0),
        ('code-proof-demo', ['line-3/tools/code-proof/code_proof.py', '--bundle', 'line-3/tools/code-proof/zto-proof.json'], 0),
        ('code-ancestry-zto-demo', ['line-3/tools/code-ancestry/code_ancestry.py', '--bundle', 'line-3/tools/code-proof/zto-proof.json', '--ancestry', 'line-3/tools/code-ancestry/zto-ancestry.json'], 0),
        ('code-ancestry-imd-demo', ['line-3/tools/code-ancestry/code_ancestry.py', '--bundle', 'line-3/tools/code-proof/imd-proof.json', '--ancestry', 'line-3/tools/code-ancestry/zto-ancestry.json'], 0),
        ('call-expectation-demo', ['line-4/tools/call-expectation/call_expectation.py', 'demo'], 0),
        ('call-expectation-fresh-saved', ['line-4/tools/call-expectation/call_expectation.py', 'check', 'line-4/tools/call-expectation/zto-live-observation.json', 'line-4/tools/call-expectation/zto-live-expectation.json'], 0),
        ('zto-band-demo', ['line-1/tools/zto-band/zto_band.py', '--snapshot', 'line-1/tools/zto-band/observation.json', '--amount', '1'], 0),
        ('zto-path-demo', ['line-1/tools/zto-path/zto_path.py', '--snapshot', 'line-1/tools/zto-path/observation.json'], 0),
        ('zto-path-incomplete', ['line-1/tools/zto-path/zto_path.py', '--snapshot', 'line-1/tools/zto-path/observation.json', '--amount', '1000000000'], 2),
        ('zto-sizes-demo', ['line-1/tools/zto-sizes/zto_sizes.py', '--amount', '1', '--amount', '100000000', '--amount', '1000000000', '--slippage-bps', '100'], 0),
        ('allowance-lens-demo', ['line-2/tools/allowance-lens/allowance_lens.py'], 0),
        ('allowance-changes-demo', ['line-2/tools/allowance-changes/allowance_changes.py'], 0),
        ('permission-gate-demo', ['line-2/tools/permission-gate/permission_gate.py'], 0),
        ('permission-gate-explicit-deny', ['line-2/tools/permission-gate/permission_gate.py', '--observation', 'line-2/tools/permission-gate/live-observation.json', '--policy', 'line-2/tools/permission-gate/demo-policy.json'], 3),
        ('code-lens-demo', ['line-3/tools/code-lens/code_lens.py', '--verify', 'line-3/tools/code-lens/zto-observation.json'], 0),
        ('code-changes-demo', ['line-3/tools/code-changes/code_changes.py', '--before', 'line-3/tools/code-lens/zto-observation.json', '--after', 'line-3/tools/code-changes/zto-after.json'], 0),
        ('code-opcodes-zto', ['line-3/tools/code-opcodes/code_opcodes.py', '--report', 'line-3/tools/code-lens/zto-observation.json'], 0),
        ('code-opcodes-imd', ['line-3/tools/code-opcodes/code_opcodes.py', '--report', 'line-3/tools/code-lens/imd-observation.json'], 0),
        ('call-rehearsal-demo', ['line-4/tools/call-rehearsal/rehearse.py', 'replay', 'line-4/tools/call-rehearsal/zto-observation.json'], 0),
        ('call-rehearsal-revert', ['line-4/tools/call-rehearsal/rehearse.py', 'replay', 'line-4/tools/call-rehearsal/zto-revert-observation.json'], 1),
        ('call-changes-demo', ['line-4/tools/call-changes/call_changes.py', 'demo'], 0),
        ('call-witness-demo', ['line-4/tools/call-witness/call_witness.py', 'demo'], 0),
        ('contract-context-demo', ['shared/contract-context/context.py', 'demo'], 2),
        ('change-context-demo', ['shared/change-context/change_context.py'], 0),
        ('change-context-require-aligned', ['shared/change-context/change_context.py', '--require-aligned'], 2),
    ])
    for folder in sorted(Path('shared').iterdir()):
        if folder.is_dir() and list(folder.glob('test_*.py')):
            commands.append((folder.name + '-suite', ['-m', 'unittest', 'discover', '-s', str(folder), '-p', 'test_*.py', '-v'], 0))
    if Path('shared/witness-context/witness_context.py').exists():
        commands.append(('witness-context-demo', ['shared/witness-context/witness_context.py', 'demo'], 0))
    if Path('shared/revoke-rehearsal/revoke_rehearsal.py').exists():
        commands.append(('revoke-rehearsal-demo', ['shared/revoke-rehearsal/revoke_rehearsal.py', 'demo'], 0))
    if Path('shared/review-rehearsal-context/review_rehearsal_context.py').exists():
        commands.append(('review-rehearsal-context-demo',
                         ['shared/review-rehearsal-context/review_rehearsal_context.py', 'demo'], 2))
    if Path('shared/swap-code-context/swap_code_context.py').exists():
        commands.append(('swap-code-context-demo',
                         ['shared/swap-code-context/swap_code_context.py', '--demo'], 2))
    return commands


def main():
    if not all(Path(f'line-{n}/GOAL.md').is_file() for n in range(1, 5)):
        raise ValueError('run from the workspace root')
    results = []
    for name, args, expected in checks():
        command = ([sys.executable, '-B', 'gathering/run_suite.py'] + args[2:]
                   if args[:2] == ['-m', 'unittest'] else [sys.executable, '-B'] + args)
        try:
            done = subprocess.run(command, text=True, capture_output=True, timeout=35)
            result = {'name': name, 'command': ['python3', '-B'] + args,
                      'expected_exit': expected, 'exit': done.returncode,
                      'passed': done.returncode == expected, 'stderr': done.stderr}
            if args[0] == '-m' and done.returncode == 0:
                match = __import__('re').search(r'Ran ([0-9]+) tests?[^\n]*', done.stderr)
                result['stderr'] = (match.group(0) + '\nOK\n') if match else done.stderr
                result['test_count'] = int(match.group(1)) if match else 0
            if args[0] != '-m':
                output = json.loads(done.stdout) if done.stdout else {}
                result['stdout_sha256'] = hashlib.sha256(done.stdout.encode()).hexdigest()
                result['summary'] = {k: output[k] for k in (
                    'schema', 'status', 'decision', 'verdict', 'candidate_count', 'demonstration_passed',
                    'largest_candidate_input_raw', 'verified', 'coherent',
                    'measured_pair_count', 'violating_pair_count', 'missing_pair_count',
                    'block', 'block_number', 'estimate', 'counts', 'summary', 'limits') if k in output}
            results.append(result)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            results.append({'name': name, 'passed': False, 'error': str(exc)})
    print(json.dumps({'schema': 'gathering-local-checks-v3',
        'authority': 'Local contributor checks; no independent certification.',
        'all_passed': all(r['passed'] for r in results), 'checks': results}, indent=2))
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
