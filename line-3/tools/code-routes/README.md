# Code Routes

Code Routes helps a worker inspect where instructions sit in an Ethereum contract's
runtime before trusting an address. It verifies a raw Code Proof bundle, then maps
structural routes from byte offset zero. It distinguishes direct jump paths from
paths admitted only because a computed jump target is unresolved. It annotates
storage, calls, creation and delegation instructions, and Code Surface's candidate
selector patterns. It does not claim a route can actually execute.

Run this offline demonstration from the repository root with Python 3.10 or newer:

```sh
python3 -B line-3/tools/code-routes/demo.py
```

No installation, network, environment settings or credentials are required. The
standard library and ordinary committed sibling sources provide all dependencies:
Code Surface, Code Opcodes, Code Ancestry, Code Proof, Code Lens and Keccak. Keep
these sibling folders if copying the tool to another workspace.

## What happened when tried

Collected fresh real ZTO proofs first and IMD second on 2026-10-14 using the supplied
Ethereum relay. Both observations reached RPC-reported finalized block **26,188,209**,
hash `0x1dfd9e5522e0883294299de66aafcf57f28fa4f9a431b1858a728cae919e5b6e`.
Public source attribution is [Ethereum PublicNode](https://ethereum-rpc.publicnode.com);
the relay's upstream is not independently authenticated. Saved raw bundles are
`zto-proof.json` and `imd-proof.json`, each under 100 KB. The demo rechecks the
header, account inclusion, runtime hash and measured proxy slots before analyzing
code. No independent anchor was invented: both results remain `unanchored-rpc-header`.

| Runtime | Bytes | Jumps | Computed targets | Direct model instructions | Additional dynamic candidates | Excluded by model |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZTO | 1,287 | 61 | 16 | 269 | 599 | 8 |
| IMD | 22,990 | 1,324 | 311 | 2,173 | 11,959 | 30 |

The demonstration passed; its exact output is in `demo-result.json`. In IMD, the
linear byte scan sees a CALLCODE in the recognized metadata suffix, but this model
excludes its location. The model still admits five CALL and six STATICCALL
instructions through unresolved dynamic routes. Neither result establishes what
any call does or whether an actual transaction reaches it. These observations
also matched the older committed proofs at block 26,187,032; no stability between
the two endpoints is inferred.

Inspect one bundle, optionally asking about decimal or hexadecimal byte offsets:

```sh
python3 -B line-3/tools/code-routes/code_routes.py --bundle line-3/tools/code-routes/zto-proof.json --pc 0 --pc 0x10
```

`--anchor-hash` accepts a separately obtained execution block hash. A matching
hash checks equality, not its authenticity. Exit 0 means proof validation and
structural analysis completed, **not approval**. Invalid inputs, proof corruption,
an anchor mismatch or unsupported `0xef`-prefixed code exit 1 with no result JSON.
The CLI only reads explicitly named workspace-local bundles, capped at 100,000
bytes, with duplicate keys rejected. It prints a report and writes no files.

## How to read the routes

* `direct-model-path`: reachable in the graph using fallthrough and valid adjacent
  PUSH0..PUSH32 jump targets, without adding computed-jump edges. This is not an
  execution witness; conditional branches are both admitted.
* `dynamic-target-candidate`: added only when the model encounters a computed
  jump. Every decoded JUMPDEST becomes a candidate, including destinations inside
  a recognized metadata suffix. This is deliberately broad.
* `excluded-by-model`: neither graph walk visits the instruction. This is useful
  bytecode context, not a safety claim or proof under every EVM version.
* `push-operand-byte` and `outside-runtime`: requested offsets that cannot denote
  a decoded instruction in this runtime.

PUSH operands never become instructions or JUMPDESTs. A constant invalid JUMP
has no outgoing edge; invalid JUMPI still permits fallthrough because the
condition might be zero. STOP, RETURN, REVERT, INVALID and SELFDESTRUCT stop the
local route. Metadata is annotated, never stripped. All other opcodes, including
undefined bytes, conservatively fall through: the model does not evaluate stack
underflow, exceptional halts, branch conditions, calldata, storage, gas or call
effects. Each proved runtime is considered independently from PC 0, including
beacon code; proxy and beacon routing semantics remain unproved.

The named model is `legacy-evm-adjacent-push-v1`; it is not a fork detector.
EOF, EIP-7702 delegation indicators and future control-flow instructions require
a different model. `0xef`-prefixed code is refused rather than misclassified.
The jump-destination rules follow the
[Ethereum opcode reference](https://ethereum.org/developers/docs/evm/opcodes) and
[Yellow Paper explanation](https://ethereum.org/developers/tutorials/yellow-paper-evm/).
The delegation prefix is specified in [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702).
No network dependency is fetched at runtime.

Analysis is bounded by the inherited 24,576-byte runtime limit. Dynamic edges
share a destination set expanded at most once, avoiding a quadratic graph.
Reports retain exact aggregate counts, previews of at most 16 entries per kind,
explicit omitted counts and up to 32 queried offsets. Header authenticity,
consensus, finality, source equivalence, ABI meaning, actual reachability, current
code and semantic safety remain unverified.

## Checks

```sh
python3 -B -m unittest discover -s line-3/tools/code-routes -p 'test_*.py' -v
```

All 25 tests passed, including real ZTO/IMD proofs, tampered headers/account proofs,
consistently rehashed forged runtime, beacon deduplication, unproven beacon warnings,
invalid and conditional jumps, unreachable dynamic jumps, PUSH0 loops, PUSH data,
truncated operands, metadata destinations, unsupported formats, maximum-size
computed-jump density, CLI failure contracts and input boundaries. An independently
implemented explicit graph agrees with the optimized walk on 250 deterministic
synthetic byte streams. Synthetic programs exist only in tests.

Mark meaning: **Pepe follows a forked trail and marks where a path ends.**
