# ZTO Evidence Bundle

Carry a reviewed ZTO/IMD planning handoff together with the exact snapshot,
size report and policy it uses. A receiving worker can recompute the bound
from one transferred file rather than finding three separate evidence files.
The bundle is capped at 100 KB and uses standard-library Python plus ordinary
committed Line 1 sibling sources. No installation or network is needed.

From the repository root, Python 3.10+:

```sh
python3 -B line-1/tools/zto-bundle/zto_bundle.py --demo
```

When tried, this returned `accepted`: 100,000,000 ZTO input and
1,184.169088029408336486 IMD planning minimum from real saved Ethereum pool
evidence at block 26,184,260. The demo policy has a historical reference block;
this does not claim to measure current liquidity.

To check the committed bundle as a receiver:

```sh
python3 -B line-1/tools/zto-bundle/zto_bundle.py --verify line-1/tools/zto-bundle/demo-bundle.json --policy line-1/tools/zto-review/demo-policy.json
```

`--policy` is mandatory and must come from the receiver's own review decision,
separately from the transferred bundle. Matching the policy inside a bundle
to itself would not establish that the receiver intended its block anchor,
age ceiling, candidate amounts, direction or tolerance. The bundled example
policy is supplied only to demonstrate the protocol.

To pack your own workspace evidence:

```sh
python3 -B line-1/tools/zto-bundle/zto_bundle.py --pack --snapshot SNAPSHOT.json --report REPORT.json --policy POLICY.json --amount 100000000 --save line-1/tools/zto-bundle/caller-bundle.json
```

All named files must be inside the current workspace. A save occurs only
after review and exact candidate selection pass. `--verify` cannot save or
accept packing arguments. `--demo --save PATH` can save a historical example.
The verifier checks the exact bundle fields and digest, agrees with the
receiver policy, recomputes the size report and selected handoff, and compares
handoff values and types. It rejects incomplete sources, report alterations,
replacement policy, extra transaction fields and rewritten limitations even
when an attacker recomputes the digests. Floats, duplicate JSON keys,
nonfinite numbers and files larger than 100 KB are refused.

Nine focused tests passed, including a no-network demo and refusal paths:

```sh
python3 -B -m unittest discover -s line-1/tools/zto-bundle -p 'test_*.py' -v
```

This is evidence portability, not independent numerical verification. Digests
do not prove Ethereum consensus or provider authenticity; the receiver's
policy is still a trust input. Snapshot age is relative to that policy's
reference block. Bounds remain historical and limited to measured tick
coverage. No wallet, secret, environment, signing, transaction, settlement,
payment or deployment is used or prepared. No new coin is needed.
