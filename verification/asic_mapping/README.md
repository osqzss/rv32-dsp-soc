# Standard-cell mapping, equivalence and timing evidence

AI-assisted engineering on the single-cycle RV32I CPU, not independent authorship.
The default CPU RTL is unchanged from `ad53882521088420a4a69c907765ddaece99feb8`.
This is a pre-layout mapping study, not routed timing closure or silicon validation.

## Recorded result

The drive/load-aware mapping preserves all 204 public output bits and all 1,025
next-state bits relative to the original RTL under common reset and unrestricted
matched state/inputs. ABC combinational equivalence compares the complete exposed
transition functions. The 199 undefined gold mux defaults are unrestricted symbolic
inputs, not zeros. The proof trusts Yosys frontend/lowering, Liberty import and ABC.

| Mapping | Instances | Typical setup / hold (ns) | Slow setup / hold (ns) | Fast setup / hold (ns) | Slew / cap violations at each corner |
|---|---:|---:|---:|---:|---|
| Original | 5,788 | 3.160122 / 0.004488 | -4.423251 / 0.220426 | 4.424589 / -0.037642 | 87/127, 127/125, 77/127 |
| Drive/load-aware | 6,367 | 4.211698 / 0.015754 | -0.216991 / 0.238338 | 4.950031 / -0.029735 | 0/0 at all three |

The electrical violations clear, but slow-corner setup and fast-corner hold still
fail. Constraints: 10 ns ideal clock, 2 ns input/output budgets, 0.1 ns uncertainty
and transition, 10 fF output load. Wire capacitance is zero; no placement, routing,
CTS or extraction. Asynchronous reset recovery/removal are excluded.
No Fmax, area in square microns, or whole-SoC timing claim follows from these results.

[COMPARISON.json](artifacts/COMPARISON.json) and the [raw reports](artifacts/timing/)
retain the original, repair and isolated candidate. The candidate improved setup
at all three corners and passed formal/architectural checks, but worsened fast
hold by 0.000170 ns against a registered 0.000001 ns tolerance.
[QUALIFICATION.json](artifacts/QUALIFICATION.json) therefore records promotion as
false. The rejected candidate is not the default CPU or a claimed optimisation win.

## Replay the mapped transition-function proof

On Linux with Python 3, Yosys and `yosys-abc` on PATH:

```sh
bash verification/asic_mapping/replay_proof.sh
```

The replay uses fresh `runs/replay-*` directories and refuses to overwrite them.
It decompresses the retained normalized snapshots, builds all six proof inputs,
checks two equivalent cases and rejects four mutations: output inversion, register
D inversion, state-bit swap and an internal gate fault. The internal gate fault
uses the original baseline netlist; it is not a new fault in the repaired mapping.
The generated BLIF hashes must match the recorded proof inputs exactly.

This replays the saved normalization output, not a fresh RTL-to-Liberty synthesis.
The public JSON snapshots remove only `attributes.src` metadata that contained
local tool paths. [Provenance](artifacts/normalized/provenance.json) binds original
snapshot hashes, public snapshot hashes, the timed repaired netlist and unchanged
CPU RTL. No logic, port, bit or connection changes were made while packaging.
The CPU source hash uses Git's LF line endings; replay accepts a Windows CRLF checkout.
The [mapped netlists](artifacts/netlists/) and [proof logs](artifacts/proof/) are retained.

## Tools, library and limitations

Recorded tools: Yosys 0.67+94 (`7defa5186-dirty`), ABC 1.01 (25 July 2026 build),
OpenSTA 3.1.0. Nangate45 typical/slow/fast Liberty files came from OpenSTA commit
`3f4b337e30afccf8075118860daf2e4fea8a5c18`, `examples/nangate45_{typ,slow,fast}.lib.gz`.
The Liberty files are not redistributed here. Obtain the same files from the
[pinned OpenSTA tree](https://github.com/parallaxsw/OpenSTA/tree/3f4b337e30afccf8075118860daf2e4fea8a5c18/examples)
to rerun timing. From this directory, with the corresponding decompressed library:

```sh
TIMING_LIBRARY=inputs/nangate45_typ.lib TIMING_NETLIST=artifacts/netlists/repair.v TIMING_ARM=repair sta -exit timing_model.tcl
```

Repeat with `slow` and `fast`, then `sta_drc_margin.tcl` for six-decimal rule margins.
The typ Liberty SHA256 is `2efd0b32eb580e4e60e72fc0575bb3bc69aac907c91d908442e4ae6d7fe55895`.
The slow and fast hashes are respectively
`899e4a91977dde6aaca8e99073ae7a02fa546510bb4a393e6bab4a8ee2f98b16`
and `7c08823aa809fb8c1d633b7f985c3f8a56c1f06e4d3a05b00c487e9e4b4805b7`.
The original drive/load-aware synthesis recipe is also portable:

```sh
mkdir -p runs/rebuild
yosys -s map_repair.ys
```

Its output is a fresh build, separate from the retained measured netlist. Tool
version differences can change mapping; rerun equivalence and timing before
assigning the retained measurements to another build.

The retained cone auditor checks reachable undriven fanins, port identities and
recorded negative outcomes. It does not independently reject an undriven terminal
output. Its assertions require ordinary Python execution, so the replay uses `-B`
and never `-O`. Four sensitivity controls are bounded checks, not certification
of the proof harness. Cell-level equivalence is not an independent frontend,
metastability, analogue timing or clock-gating proof.
