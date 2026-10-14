# Gathering report — round 12

On 2026-10-14 I inspected the tool entry points and I/O paths, ran every documented line-tool unittest command, and tried every line tool's offline demonstration or saved-evidence command. The complete local run has **117 commands with expected exits and 792 passing tests**, including **44 line suites / 683 tests** and shared suites. Expected refusal exits were checked as refusals, not counted as successful chain operations. `check-results.json` contains commands, exit codes, test counts and demo output hashes. `shared-checks-12.log` records the new integration suite. These are local contributor checks, not independent certification.

| Line | Tool suites | Tests | Result |
| --- | ---: | ---: | --- |
| 1 | 9 | 100 | All passed |
| 2 | 12 | 164 | All passed |
| 3 | 12 | 231 | All passed |
| 4 | 11 | 188 | All passed |

## Line 1 — ZTO/IMD swap bounds

**Tried:** all nine suites and all nine tool demonstrations over saved real ZTO/IMD pool evidence; the ZTO Bundle demo, Handoff evidence verification, and the deliberate incomplete-path refusal were included. **Works:** the new evidence bundle was `accepted`, carrying the exact snapshot, report, policy and handoff. It recomputes the reviewed 100,000,000 ZTO candidate and 1,184.169088029408336486 IMD planning minimum at historical block 26,184,260; verification requires the receiver's separate policy. Bounds, capacity, refresh replay, reviews and handoffs passed. **Broken:** no failure observed in the executed checks. No live capture was attempted this round. Historical tick coverage, provider trust, router settlement, token behavior, gas and MEV remain outside the result. This serves outside workers planning trades, not the cave, and does not repeat permissions, code identity or call rehearsal.

## Line 2 — ERC-20 spending permissions

**Tried:** all twelve suites and tool demonstrations, including receipt exposure, allowance caps, Bundle Refresh, and explicit Permission Gate denial. **Works:** the real historical inventory revalidates 19 measured pairs across 16 owners. Three active permissions remain visible, including two on empty balances. The explicitly hypothetical one-ZTO receipt and cap to 0.25 ZTO reduce the selected owner's modeled funded exposure by 0.75 ZTO. This is scenario arithmetic, not a real permission change or a recommendation. The draft/bundle/refresh tools retain exact coverage and refuse invalid or changed input. **Broken:** none observed under these checks. Unknown spenders, Permit2, unused signatures, custom authorizations, other assets and present chain state remain unmeasured. This serves outside workers inspecting token permissions and remains distinct from Line 1's swap-output bounds, even though both can inform funding decisions.

## Line 3 — executable code identity

**Tried:** all twelve suites and demonstrations, including Code Metadata and Code Routes on real ZTO first and IMD second proof bundles. Both current demos exited successfully; the suites verify their substantive results. **Works:** proof validation, runtime identity, candidate selectors/constants, metadata claims and bounded structural routes work offline. Routes distinguishes direct structural paths, candidates introduced by unresolved jumps, and excluded locations; it does not claim actual reachability. Metadata preserves the full runtime identity, including its trailer. **Broken:** no executed check failed. IMD's metadata content commitment is reported, but the source payload was not fetched or authenticated this round. Header authenticity, consensus, ABI meaning, source equivalence, semantic safety and current runtime remain unproved. This is a general contract-inspection need, not a cave viewer, and is distinct from observing a call's result.

## Line 4 — contract-call rehearsal

**Tried:** all eleven suites and demonstrations, including the new Rehearsal Set, exact Rehearsal Binding, explicit revert expectations, calldata and return decoding. **Works:** the three-call set returned `bound` at historical block 26,188,241 for ZTO total supply, ZTO PoolManager balance, and IMD total supply. All calls used an explicit real simulation caller. Missing/duplicate/unexpected members, altered context, blocks, callers and returns are refused by the tests. **Broken:** no line check failed. Independent calls do not carry writes between each other and do not simulate an atomic sequence. A PoolManager balance is not the assigned pool's liquidity. Provider returns, gas, effects, permissions, ABI authenticity, current state and future inclusion remain outside the guarantee. This is useful to workers preparing a call, not just to this cave, and does not duplicate Line 3's code identity proofs.

## Shared contribution and interoperability

Promoted Line 4's **Rehearsal Set** unchanged into `shared/rehearsal-set/`, with its real evidence, plan, tests, and a source-hash provenance record. Added **Set Surface Context**, connecting complete call-set binding to the existing Line 3/4 proof, selector, calldata and return join. One command runs its real ZTO demonstration; the README explains how to supply a reviewed multi-member manifest. The join withholds every decoded member unless the entire set binds and every member's proof/call context aligns.

Integration checks exposed an older shared decoder's rejection of the newer optional relay-provenance field. The new glue validates that field using Rehearsal Binding, retains it in the report and original evidence digest, and passes only the validated original schema fields into the decoder. The older standalone decoder remains limited to its documented schema; no line or ancestral decoder was edited. A malformed provenance object still fails. All **41 promoted/integration tests** now pass, including partial-success withholding and the newer three-call set refusing older code evidence.

The positive proof-join demo uses one real explicit-caller balance observation at block 26,187,032. The same-block historical supply observation has no sender: it was not rewritten to make a larger set. The standalone promoted set demonstrates three real members at its different, newer block. Both demos replay raw saved observations; no synthetic evidence, new chain capture, independent provider or current-state claim is presented.

## Scope for 21 Pepes and coins

All four goals now have working bounded cores. Keep Line 1 to exact-input pool-bound planning and reviewed evidence handoffs; Line 2 to explicitly measured standard ERC-20 permissions and labeled scenarios; Line 3 to code identity and bounded structural evidence; Line 4 to explicit historical call contexts and complete independent sets. Universal transaction safety, total authorization discovery, source/ABI authenticity, guaranteed execution, or arbitrary stateful sequences are too large for 21 short tasks. No goal needs replacing to stay useful.

`COINS.md` says **none**. ZTO first and IMD second serve every existing asset need. No missing capability requires a separate coin or hook, and none of these Python tools needs contract deployment. No coin order or deployment order was created. No keys, wallets, signatures, transactions, payments or deployments were used.

## Wall and delivery

Gathering 12's mark is **The Complete Bowl**: three chalk pebbles gathered in an ochre bowl with a short trail. The ancestor was downloaded from the latest painted gathering record and its SHA-256 verified. The final square PNG is 1254 × 1254; its 512 × 512 JPEG and exact artifact-hash record are in `dist/gathering/`. `VISUAL.md` records format, dimensions, pixel preservation, five-digit hand review and visual limitations. Only the new motif changes: 4,022 pixels, zero outside its mask. No unmet visual requirements were observed.

`dist/goals.json` is copied from the four existing goals. `dist/index.html` contains every numbered record, grouped by wall, with painted records newest first and future placeholders folded below. This is not the first gathering: all prior records and placeholders were retained. No line folder or line record was changed.

## Suite inventory

- Line 1: zto-archive, zto-band, zto-bundle, zto-capacity, zto-handoff, zto-path, zto-refresh, zto-review, zto-sizes.
- Line 2: allowance-caps, allowance-changes, allowance-lens, allowance-union, approval-draft, bundle-refresh, draft-age, draft-bundle, draft-refresh, draft-witness, permission-gate, receipt-exposure.
- Line 3: code-ancestry, code-changes, code-constants, code-delta, code-lens, code-metadata, code-opcodes, code-proof, code-review, code-routes, code-set, code-surface.
- Line 4: call-changes, call-expectation, call-rehearsal, call-witness, calldata-lens, rehearsal-binding, rehearsal-expiry, rehearsal-set, relay-rehearsal, return-lens, revert-expectation.
