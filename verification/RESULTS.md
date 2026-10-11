# CPU verification quality: measured results

Status: verified locally for the studies and controls below. Final full-SoC integration rerun is recorded separately in NVIDIA_PSII/evidence/full-soc-directed-memory-v2.log. No commit or push. Baseline RTL source: 48cd442e2f1eeae3aedb41d777772e99bcbd493b. CPU RTL and ISA execution logic in the C++ ISS are unchanged; the ISS now has an optional memory snapshot.

## Scope and chronology

PLAN.md and mutations.json were locally hash-sealed before mutation measurements. They are not a public preregistration. The original suite is unchanged smoke plus random seeds1-100 with body300. The 12 mutations are artificial, single-fault changes in disposable core copies, not 12 naturally discovered CPU defects. All compile and each anchor matches once. Directed tests were added after recording the first two JALR escapes. A post-review ADDENDUM.md extends instrumentation to final memory and divergent prefixes; historical results remain preserved.

| Arm/instrument | Gold programs matching | Retired instructions | Detected faults | Survivors | Other outcomes |
|---|---:|---:|---:|---:|---|
| Original trace instrument |101|38,390|9|2|1 instruction-limit execution failure, not credited as a trace detection |
| Original instrument + directed tests |102|38,453|12|0|0 invalid,0 execution failure |
| Final memory/prefix instrument, original suite |101|38,390|10|2|0 invalid,0 execution failure |
| Final memory/prefix instrument + directed tests |102|38,453|12|0|0 invalid,0 execution failure |

Every arm hits all38 implemented instruction mnemonics and12/12 branch taken/not-taken bins. This is coverage of the implemented subset, not RV32I specification conformance or complete CPU verification. Original suite survivors are jalr_link_plus8 and jalr_odd_target. The directed witness adds nonzero JALR link, odd target and source/destination aliasing, plus signedness, shifts, byte lanes, x0 and branch cases. Manual final-register expectations include JAL x5=240 and JALR copies x28=256,x29=272; both models match them.

The change from9 to10 detections in the original suite is an instrumentation correction: jal_link_plus8 on smoke differs at retire row57, then fails to terminate. The final harness records the differing common-prefix row and the noncompletion reason, rather than losing the design divergence inside a generic execution error. Missing/malformed output or an equal incomplete prefix still cannot pass or count as detection.

## Store observability, paired on all100 random programs

| Injected store fault | Trace-only detections | Trace + final-memory detections |
|---|---:|---:|
| SB byte lane forced to0 |14/100|96/100|
| SH upper/lower bytes swapped |25/100|100/100|

The remaining4 byte-store escapes remain reported; no claim is made that memory snapshots observe every transient wrong store. Later writes can mask a store, and some operands make a fault's result equal. The observed aggregate does not distinguish those explanations. A separate no-reload witness has identical complete retire traces under each store mutation but different final memory, and is rejected for both. Compare all4096 words (16KB), including zeros via sorted sparse snapshots with WORDS header and END nonzero-record count. Missing trailers, equal line-boundary truncation, wrong counts, invalid addresses, unknown values and malformed records fail.

## Harness/integration controls

-16 Python unit tests pass, including empty, truncated, malformed, missing and divergent traces; process failure/timeout; memory mismatch, malformed/truncated snapshots and zero memory.
-8 real integration controls pass: independent directed register oracle in both engines; ISS step exhaustion; RTL step exhaustion; tampered saved baseline source; divergent nonterminating mutant; both store mutants without reloads; shell wrapper forwarding memory comparisons.
-Fresh output directories refuse overwrite, so stale traces cannot stand in for current runs. Logs and results are retained per execution. Failed processes are never scored as equal completed executions.
-The standalone bench is core+16KB flat memory. Full-SoC smoke passed at62 instructions before changes; final full-SoC directed test and two generated programs verify the production entry points separately. No peripheral conformance claim follows from the core study.

## Evidence and reproduction

Historical local evidence: build/study-baseline/summary.json, build/study-extended-reviewed/summary.json. Final instrument: build/study-memory-v2-baseline/summary.json, build/study-memory-v2-extended/summary.json, build/store-observability-v2/results.json and build/integration-controls-memory-v2/result.json. Each study retains source programs, source SHA256s, reference/RTL traces, compiler/runtime logs and first divergences. Portable summary copies live in verification/results/; raw per-execution traces remain in the local build folder.

On a fresh checkout with Python3,g++,Icarus/vvp and Make on PATH:

```bash
python3 -m unittest discover -s verification -p test_verify.py -v
python3 verification/study.py --out build/study-baseline
python3 verification/study.py --out build/study-memory-v2-extended --baseline build/study-baseline
python3 verification/store_observability.py
python3 verification/integration_controls.py
make check TEST=arch_edges
bash scripts/regress.sh 2 300 build/cli-regression
```

Output folders must not already exist. These commands reproduce the final instrument on the same frozen program/mutation set; they do not recreate the obsolete historical instrument. No exceptions/interrupts, FENCE/CSR conformance, misaligned traps, caches, pipeline, silicon timing or third-party ISS conformance is claimed. The C++ reference and assembler are first-party implementations, with the small directed register oracle as an additional check.12/12 means this fixed fault set, not a universal detection rate.
