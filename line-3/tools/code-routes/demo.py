"""Replay real ZTO-first and IMD runtime proofs without network or invented anchors."""
import json
from pathlib import Path
import code_routes as routes


def main():
    results = []
    for token in ('zto', 'imd'):
        path = Path(__file__).resolve().parent / (token + '-proof.json')
        result = routes.inspect(routes.ancestry.read_json(path))
        runtime = result['runtimes'][0]
        results.append({'token': token.upper(), 'target': result['target'],
                        'code_block': result['code_block'], 'code_hash': runtime['code_hash'],
                        'state_inclusion_verified': result['proof']['state_inclusion_verified'],
                        'anchor': result['proof']['anchor'],
                        'runtime_bytes': runtime['runtime_bytes'],
                        'instruction_route_counts': runtime['instruction_route_counts'],
                        'jump_count': runtime['jump_count'],
                        'dynamic_jump_count': runtime['dynamic_jump_count'],
                        'dynamic_jump_expansion_used': runtime['dynamic_jump_expansion_used'],
                        'operation_counts': runtime['operation_counts'],
                        'execution_reachability_verified': result['execution_reachability_verified']})
    return {'demonstration_passed': all(r['state_inclusion_verified']
                                       and r['anchor'] == 'unanchored-rpc-header'
                                       and r['jump_count'] > 0
                                       and not r['execution_reachability_verified'] for r in results),
            'results': results,
            'scope': 'Historical proof replay and conservative structural route analysis, not execution.'}


if __name__ == '__main__':
    result = main()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['demonstration_passed'] else 1)
