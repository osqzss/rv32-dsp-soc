# External RV32I subset checking

AI-assisted engineering work. The reference and test bodies are independently maintained upstream projects; the observation adapter and comparison harness are local additions. No first-party assembler or C++ ISA model participates in this path.

Unchanged CPU RTL at ad53882521088420a4a69c907765ddaece99feb8 passes **40 adapted upstream tests / 11,708 executed instructions** against rv32emu. Every pre-instruction PC, instruction word and all32integer registers agree, including40terminal sentinel states. Every program also agrees on all4,096final memory words. Upstream embedded expected-value assertions must pass independently of engine agreement.

| Final population/outcome | Count |
|---|---:|
| rv32ui entries from upstream Makefrag |42|
| Attempted / passed |40 /40|
| Architectural failures / execution errors / skipped |0 /0 /0|
| Unsupported, declared in advance |2|
| Executed instructions before terminal sentinel |11,708|
| State observations / register comparisons |11,748 /375,936|
| Memory words per program |4,096|

The two unsupported entries are fence_i and ma_data. These are adapted tests, not an unmodified official conformance suite or certification. CPU RTL is unchanged. No organic design bug was found.

## Reproduce

From a checkout containing this folder, on Ubuntu24.04 x86-64 with git, gcc/g++, Python3, Make and Icarus/vvp:

```sh
bash verification/external_isa/bootstrap.sh
```

bootstrap fetches exact source revisions, extracts binutils locally, builds an observation-only reference adapter, runs a development test,15controls, then the complete sealed manifest. It requires a fresh folder for dependencies and outputs. It neither installs system packages nor modifies CPU RTL. The OSS CAD Suite PATH entry is a local convenience; an already-installed Icarus/vvp on PATH also works. For an already bootstrapped folder, run a fresh suite with:

```sh
python3 verification/external_isa/run.py --out verification/external_isa/runs/new-run
```

Source revisions are machine-derived in provenance.json: rv32emu a5b5f9217fb2b4d8a73fcf4e572aa90ccc33f07c, riscv-tests7b68f7b91f827f8d94cc1c57ff123752c5c8f704, Kconfiglib6d9102abd55b614d3c6133529ffa40dbea7fd2cf, mini-gdbstub8aefbcda5311c2eeb49ae6c457e4957f5c232863. GNU assembler/linker2.42, native gcc/g++13.3, Python3.12.3, Make4.3 and Icarus/vvp14.0 development s20260301-322-ga4989d023-dirty were used. Binutils package hash is checked in bootstrap.sh.

## Contract and independence

PC0 and32zeroed registers,16KB unified little-endian memory. Text below0x2000, data from0x2000. Unchanged upstream rv32ui bodies include unchanged rv64ui bodies and scalar macros; manifest hashes every body. env/riscv_test.h replaces privileged setup/pass/fail, and link.ld relocates the image. ECALL0x73 is observed as an external terminal sentinel before execution, not a handled trap. Only x3=1 is success.

reference-observation-v2.patch adds reset/observation/stop code only to riscv.c; upstream rv_step_debug performs instruction semantics with GDBSTUB/debug_mode enabled. No socket is opened by this adapter. JIT, fusion, chaining and ISA extensions are disabled. Upstream decoder generation changes formatting/comments only; executable C-token sequence was checked against HEAD. No expected register values are derived from RTL or masked by the comparison.

## Controls and retained negative results

results/controls.json records10controls: three real compiled RTL mutants (SRA, BEQ, SB), an intentionally incorrect upstream add expected value, five corrupt-evidence checks and unchanged gold rerun. results/extra-controls.json records five more: gold, a real store mutant observable only in memory despite identical state streams, and equal-empty/truncated-state/truncated-memory evidence.15controls pass, comprising2positive golds and13required rejections. Additional controls are not extra upstream tests.

results/initial.json remains **39PASS/1ERROR/2UNSUPPORTED**. The original adapter used rv_step_debug without proper debug-mode setup and crashed onJALR through an uninitialized branch-history table. Enabling upstream GDBSTUB and debug_mode corrected adapter configuration without changing ISA semantics. The same JALR ELF SHA25616f8dcf7657b09b861ab897ad749b0cbed90487f9587ca2a03e9198dc73e3118 then passed, followed by the entire unchanged manifest. results/final.json and audit.json record final outcome. AMENDMENT.md documents this correction; original registration/seals remain historical.

PROVENANCE-CORRECTION.md discloses transposed upstream SHA labels in the original local PLAN.md. The actual tested sources/test hashes never changed; provenance.json and bootstrap.sh carry corrected mappings. The plan is locally hash-sealed, not public preregistration. Full primary state/memory traces and tool logs are retained locally; this package includes portable summaries and reproduction inputs.

After the v2 measurement seal, run.py received one packaging change: CORE can resolve either the isolated project directory or this repository's rtl directory. Current run.py SHA256 is 1263af0b71b9f537e7d804b27f87cb5a341abd26a69373cbee2cff261cbdb6c5, distinct from the historical sealed adf6ee83cea9c2cc459eb9df803b08c9119e15b7544c0b89dea4050a004d1163. Replacing the two-line conditional CORE assignment with `CORE = ROOT / "project/rtl/rv32i_core.v"` reconstructs the historical hash exactly. No comparison or execution logic changed. The historical seal is preserved, not silently updated. A fresh run from the extracted source archive reproduced 40 passes, 2 unsupported entries, 11,708 instructions and all 15 controls using the portable path. It reused cached pinned dependency sources and the hash-checked binutils package; the network bootstrap was not rerun end to end.

## Limits

No FENCE memory-ordering proof, FENCE.I/self-modifying-code synchronization, exceptions/illegal-instruction traps, misaligned data/control transfers, privilege, CSR, interrupts or ECALL trap handling. No compressed/atomic/floating/multiply extensions, caches/pipeline hazards, SoC peripherals/MMIO, physical timing or silicon validation. Final-memory checks can miss overwritten transient stores. A third-party reference reduces shared first-party errors but is not proof that the reference is correct. No complete RV32I conformance claim.
