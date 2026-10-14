# Allowance Caps

Compare caller-selected hypothetical ERC-20 allowance reductions with raw measured permissions before deciding which caps deserve owner review. It shows both current-balance exposure and exposure after optional hypothetical net receipts. It uses Python 3.10+ and only the standard library plus ordinary sibling sources shipped in this line. No installation or network is needed.

From the repository root, one command shows it working:

```sh
python3 -B line-2/tools/allowance-caps/allowance_caps.py
```

The demonstration revalidates the saved **real ZTO** inventory at Ethereum block **26,187,572**: 19 measured owner–spender pairs across 16 owners. It uses the preceding tool's explicit hypothetical one-ZTO receipt to real measured owner `0x632ee80c099662ee9880d04a307401de195dabf8` and `hypothetical-cap.json`, which proposes reducing that owner's measured maximum allowance to spender `0x765956a7307222346b08fff681820a5d77e92028` to **0.25 ZTO**. These are historical evidence addresses, not a guessed user account. The amount is a labelled example choice, not a recommendation or an observed change.

## What happened when tried

On 2026-10-14 the default demonstration returned one changed hypothetical pair. For the selected empty-balance owner, current exposure reduction was zero, but the combined bound after the assumed receipt decreased from `1000000000000000000` to `250000000000000000` raw units: a reduction of `750000000000000000`. The permission remains active in the model. All other measured allowances were retained. `example-report.json` records the computed hypothetical comparison; it is not raw chain evidence or a new chain read. No permission was actually changed.

Twelve focused tests passed, covering the real-evidence replay, retained unlisted pairs, zero and unchanged targets, overlapping spender bounds, another spender preserving the whole exposure, allowance sums above uint256, attempted increases, unknown and duplicate pairs, strict schemas/amounts, missing raw reads, receipt overflow, input immutability, digest/order behavior, CLI option pairing and workspace confinement. The thirteen Receipt Exposure tests also passed. Synthetic evidence mutations occur only inside tests.

## Compare your own explicit scenario

```sh
python3 -B line-2/tools/allowance-caps/allowance_caps.py --observation line-2/tools/bundle-refresh/live-after.json --caps line-2/tools/allowance-caps/hypothetical-cap.json --receipts line-2/tools/receipt-exposure/hypothetical-one-zto.json
```

Provide `--observation` and `--caps` together. Omit `--receipts` to compare only the measured balances: no hypothetical funding is then assumed. Custom receipt inputs require explicit observation and caps inputs. All files must resolve inside the current workspace, be at most 96 KiB and have no duplicate JSON keys. The observation must contain raw Allowance Lens or Allowance Changes inventory evidence; reports alone are refused.

The caps object has exactly `schema`, `chain_id`, `token_address`, and `pairs`. Schema is `permission-hypothetical-caps-v1`, chain is integer `1`, and token must match the real ZTO or IMD observation. The list contains 1–64 explicit pairs, each with exactly `owner`, `spender`, and `target_allowance_raw`. Targets are canonical decimal uint256 strings in token base units, never human decimal token amounts. A target must be at most its measured allowance. Unknown pairs, duplicate pairs, extra fields, increases and mismatched token/chain are refused. Unlisted measured pairs keep their original allowance; they are never treated as revoked.

Receipt inputs use Receipt Exposure's `permission-hypothetical-receipts-v1` schema and explicit net balance increases. Unknown receipt owners and uint256 balance overflow are refused. Omitted measured owners receive zero in the scenario. SHA-256 digests bind all parsed input objects; they do not authenticate those objects.

For balance `B`, net receipt `R`, measured allowance sum `A`, and proposed sum `C`, current combined bounds are `min(B,A)` and `min(B,C)`. Funded combined bounds are `min(B+R,A)` and `min(B+R,C)`. The reported reductions are the differences. Pair bounds overlap and their reductions **must not be summed** as an owner reduction. Independent total capacities are `min(uint256_max,A)` and `min(uint256_max,C)`: they show fixed-permission capacity across possible balances, not predicted funding. Another unchanged permission can leave combined exposure or capacity unchanged even when one allowance is reduced to zero.

Exit 0 prints a valid hypothetical comparison; exit 1 refuses malformed or inconsistent inputs. This is no policy approval, transaction draft, enforceable limit, safe approval sequence, or assurance of future execution. Historical trusted RPC evidence is not a state proof or current-chain measurement. Standard ERC-20 behavior is assumed. Unknown spenders, Permit2, unused signatures, custom authorizations, other assets and chains remain unmeasured. A zero bound does not establish wallet safety. An owner must independently review actual current permissions and any eventual action.

The tool prints JSON and writes nothing. It never reads a key, wallet, secret or environment variable, contacts a network, simulates/signs/sends a transaction, pays, posts or deploys.

```sh
python3 -B -m unittest discover -s line-2/tools/allowance-caps -p 'test_*.py' -v
```
