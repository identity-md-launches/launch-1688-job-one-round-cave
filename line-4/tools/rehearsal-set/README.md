# Rehearsal Set

Check that a reviewed set of independent Ethereum calls has **complete matching
rehearsal evidence at one exact historical block**. This catches accidentally
omitted calls, duplicate or unexpected entries, swapped labels, changed callers,
and evidence assembled from different blocks. It uses Python 3.9+ and the
standard library, needs no installation, and works offline.

Run from the repository root:

```sh
python3 -B line-4/tools/rehearsal-set/rehearsal_set.py demo
```

Tried on 2026-10-14: the demo returned `bound`, with all three calls matched at
Ethereum finalized block **26,188,241** (`0x18f99d1`). The saved real observations
were collected in this task, using hash-pinned `eth_getCode` and `eth_call`,
`requireCanonical: true`, mainnet chain identification, and a matching header
recheck after all calls. ZTO was queried first, then IMD:

| ID | Call | Raw integer returned |
| --- | --- | --- |
| zto-supply | ZTO `totalSupply()` | 1000000000000000000000000000 |
| zto-manager-balance | ZTO `balanceOf(PoolManager)` | 304756253603277900345322340 |
| imd-supply | IMD `totalSupply()` | 4174192949067000000000000 |

All three calls explicitly used the real PoolManager address
`0x000000000004444c5dc75cb358380d2e3de08a90` as their **simulation caller**. This
contract address does not establish a usable transaction origin or an owner's
permission. Its ZTO balance is the manager's total token balance, not the given
ZTO/IMD pool's balance or liquidity. Values above are unscaled integer base units.

Source attribution: https://ethereum-rpc.publicnode.com. Collection used the
contributor-provided Ethereum relay, not a verified direct connection to that
public provider. Each observation retains `contributor-relay` provenance and
explicitly disclaims upstream identity and independence. Only the read-only
methods in the inherited Call Rehearsal allowlist were used, with its dedicated
User-Agent and no redirects or automatic proxy discovery.

The example plan was derived from the measured results to demonstrate binding;
it is **not an independent prediction** of these balances or supplies. The demo
replays the checked-in evidence and makes no current-state claim or network call.

## Check your own set

```sh
python3 -B line-4/tools/rehearsal-set/rehearsal_set.py check path/to/evidence.json path/to/reviewed-plan.json
```

The two checked-in `zto-set-*.json` files are complete examples. A plan has exactly:

- `schema`: `rehearsal-set-v1`.
- `chain_id`: integer `1`.
- `block`: exact `number`, `hash`, and `timestamp`, in canonical RPC hex forms.
- `calls`: 1–32 objects with exactly `id`, `call`, and `expected_return`.

Each `call` has exactly explicit `from`, `to`, `data`, and native ETH `value`.
Addresses must be real nonzero addresses, data must be even-length hex, and
value must be a canonical RPC hex quantity. The expected return is an exact
hex byte string; empty successful returns are allowed. Identical call contexts
cannot appear twice in a plan. IDs are unique lowercase ASCII identifiers of
1–48 characters, beginning with a letter, then letters, digits, `_` or `-`.

Evidence has exactly `schema: rehearsal-set-evidence-v1` and `observations`, a
list of 1–32 objects containing exactly `id` and `observation`. Each observation
is a complete `call-rehearsal-v1` record accepted by Rehearsal Binding, including
optional validated contributor-relay provenance. Do not put credentials in it.

This tool collects no evidence and sends no requests. Assemble observations
from your separately reviewed read-only collection at the same exact block;
never change their block labels to make mismatched evidence agree. Unknown
fields, duplicate IDs, duplicate JSON keys, non-finite JSON numbers, oversized
inputs, and paths resolving outside the current workspace are rejected. Each
input is at most 95 KB. No gas, nonce, fee, access-list, or wrapper fields are
silently discarded.

## Results

- `bound`, exit 0: every planned call has a successful return with the expected
  exact bytes, sender, target, calldata, value, and all three block fields.
- `mismatch`, exit 1: an extra observation is present, a context or return differs,
  or the provider reports a revert. This takes precedence over missing entries.
- `inconclusive`, exit 2: missing entries or sender evidence, provider failure,
  malformed return interpretation, or invalid input. Invalid input produces a
  concise JSON error on stderr, rather than a partial report.

Reports list missing/unexpected IDs, individual binding reasons and field
differences, matched counts, source provenance, and SHA-256 input fingerprints.
A report with some matching calls is never a bound set unless every call matches.
Fingerprints use sorted compact ASCII JSON of the normalized plan and original
parsed evidence. They are content identifiers, not signatures; reordering lists
can change the fingerprint without changing the binding verdict.

**The calls are independent.** They all see the same historical chain state;
writes from one simulation do not feed the next. This is not a stateful sequence,
multicall, atomic transaction, effects analysis, ABI authentication, gas estimate,
permission check, or guarantee of future success. Even ABI `false` matches if
those exact bytes were expected. A forged provider observation can pass structural
checks. Rehearse a real outer multicall separately to study its combined execution.

Keep the sibling `rehearsal-binding/` and `call-rehearsal/` folders when copying
this piece. It reuses their reviewed validators and binding implementation,
without modifying them. No third-party or network-fetched dependency is needed.
The checker never reads environment variables, keys, secrets, or wallets, and
never signs, sends, pays, posts, or deploys anything.

## Checks performed

```sh
python3 -B -m unittest discover -s line-4/tools/rehearsal-set -p 'test_*.py' -v
```

All 27 focused tests passed, covering the real offline set, incomplete coverage,
duplicates, context/return mutations, swapped IDs, reverts and RPC failure,
malformed returns, false returns, provenance, strict input bounds, CLI statuses,
and a network-disabled demo. Mutations in the tests are synthetic refusal
fixtures, not real chain observations. The live collection and saved replay also
passed; `live-result.json` records the locally checked result, not certification.
