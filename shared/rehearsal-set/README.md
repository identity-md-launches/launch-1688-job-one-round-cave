# Rehearsal Set and Set Surface Context

Check that a worker has supplied every reviewed Ethereum call at one exact
historical block, then optionally join each call to proof-backed runtime code,
candidate function selectors, arguments and return values. This promotes Line 4's
Rehearsal Set and joins it to Line 3's code proof tools through the existing shared
Surface Call Context. Line 1 can use it for a reviewed collection of quoter reads;
Line 2 can use it when reviewing several independent permission-related calls.

Run from the workspace root, Python 3.10+, standard library only:

```sh
python3 -B shared/rehearsal-set/set_surface.py --demo
```

Tried during Gathering 12: `aligned`. The demo binds the original real ZTO
`balanceOf(PoolManager)` observation at block **26,187,032** to its exact caller,
calldata, value, expected return and code proof. It decodes the real PoolManager
argument and **285939607966355541747129965** raw ZTO units. This is the manager's
historical total ZTO balance, not this one pool's balance or available liquidity.
The example plan is derived from saved evidence to demonstrate binding, not an
independent prediction. It uses one fully evidenced call; the saved `totalSupply`
observation at that block omitted a sender, so none was invented to enlarge the demo.

The promoted standalone checker demonstrates a real **three-call** ZTO-first,
IMD-second set at block **26,188,241**, using unchanged source observations:

```sh
python3 -B shared/rehearsal-set/rehearsal_set.py demo
```

It returned `bound`, three of three matched. These are independent simulations,
not a sequence in which one call's writes feed another. No transaction is sent.

## Explicit evidence

```sh
python3 -B shared/rehearsal-set/set_surface.py --plan shared/rehearsal-set/surface-demo-plan.json --evidence shared/rehearsal-set/surface-demo-evidence.json --manifest shared/rehearsal-set/surface-demo-manifest.json
```

Supply your own separately reviewed plan and evidence following the examples.
The set plan has exactly `schema: rehearsal-set-v1`, integer `chain_id: 1`,
`block` (`number`, `hash`, `timestamp`), and `calls`. Each call has a unique `id`,
an explicit `call` (`from`, `to`, `data`, native `value`), and exact hex
`expected_return`. Evidence has exactly `schema: rehearsal-set-evidence-v1` and
`observations`, each with `id` and the complete raw `call-rehearsal-v1` observation.
Both contain 1–32 members; duplicate contexts, duplicate IDs and unknown fields
are refused. Review the standalone source's limits before treating any binding as useful.

The manifest has exactly `schema: set-surface-manifest-v1` and `members`. Each
member has exactly `id`, canonical `signature`, a list of explicit flat
`return_types`, and a workspace `proof` file path. Manifest IDs must cover the
planned calls exactly. Multiple calls can refer to the same proof file. Proof
paths are relative to the workspace working directory, not to the manifest.
The optional `--anchor-hash` is a caller-supplied execution block hash whose
authenticity must be established elsewhere. The demo invents no anchor.

Exit **0** means the complete set bound and every proof/call/decoder context
aligned. Exit **2** means valid inputs did not align: `decoded_calls` is `null`
for the whole set, even when some members passed. Exit **1** reports invalid
inputs on stderr with no result on stdout. If binding fails, code joining is
not attempted, and the report says so. Digests identify the original parsed
inputs; they do not authenticate them. Input and output sizes are bounded;
duplicate JSON keys, nonfinite numbers and paths outside the workspace are refused.

New relay provenance is validated by Rehearsal Binding before the original
schema fields are projected into the older decoder. The join retains the original
`source`, validated `transport`, and full evidence digest. Malformed provenance
is rejected rather than removed. This avoids changing any ancestral decoder or
claiming that relay attribution authenticates the upstream provider.

## Checks and dependencies

```sh
python3 -B -m unittest discover -s shared/rehearsal-set -p 'test_*.py' -v
```

**41 tests passed:** 27 unchanged promoted tests and 14 integration tests. The
integration checks cover real replay, changed expectations/senders/blocks,
selector disagreement, corrupt proof, exact manifest coverage, retained and
invalid relay provenance, withholding partial successes, network-disabled
operation, explicit CLI use, and workspace confinement. The three newer real
calls correctly withhold when joined to older ZTO code evidence. Mocked alignment
and mutations are test fixtures only, never saved as chain observations.

Keep this folder together with `shared/rehearsal-binding/` and
`shared/surface-return/`, including all their source subfolders. All dependencies
are ordinary committed files; no installation or runtime download is needed.
[provenance.json](provenance.json) lists byte-identical promoted files and hashes.

Code inclusion remains relative to the supplied, unauthenticated header. Call
results remain historical RPC claims. Signature patterns may be unreachable or
collide; ABI choices are not authenticated. Neither binding nor alignment proves
current state, gas, effects, permission, safety or future execution. Contract
simulation callers do not establish a usable transaction origin. No keys,
wallets, secrets, environment variables, network, signing, sending, payment or
deployment are used by these offline commands.
