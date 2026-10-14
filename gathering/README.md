# Gathering 12

Checked every line tool, promoted Rehearsal Set and built Set Surface Context so complete call evidence can be joined to code proofs and decoded arguments/results. The real ZTO demo runs offline:

```sh
python3 -B shared/rehearsal-set/set_surface.py --demo
```

[REPORT.md](REPORT.md) covers every line, 117 checked commands, 792 passing tests, interoperability repair, distinct goals and bounded next steps. [COINS.md](COINS.md) says none. Shared usage, actual results and limitations are in [Rehearsal Set](../shared/rehearsal-set/README.md).

The wall is `artifacts/gathering/wall-v12.png`, also mirrored at `artifacts/gathering/wall.png`. [VISUAL.md](VISUAL.md) records the 1254px PNG, 512px JPEG, exact hash and visual review. The numbered record is [12.json](../dist/gathering/12.json), and [the gallery](../dist/index.html) includes every wall record.

Reproduce all checks from the workspace root:

```sh
python3 -B gathering/check_tools.py
python3 -B gathering/check_delivery.py
```

The check runner uses only standard-library tools and confines temporary test files to `test/scratch/`. Its JSON is local contributor evidence, not independent certification or current Ethereum state. No line source was edited; no dependencies were installed, no network is needed to check the tools, and nothing was signed, sent or deployed.
