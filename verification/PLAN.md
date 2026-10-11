# RV32I verification quality study

Frozen before implementation and mutation execution, 11 October 2026.
Baseline source: 48cd442e2f1eeae3aedb41d777772e99bcbd493b.
This is a locally hash-sealed plan, not a public preregistration or committed result.

Objective: measure whether the independent C++ instruction-set reference and RTL trace checker detect realistic single-fault CPU changes, and prevent incomplete executions from being counted as architectural passes.

Baseline suite: unchanged tests/smoke.s plus model/gen_random.py seeds 1 through 100, each with 300 body instructions. Seed and instruction counts are scope, not independent architectural proofs. Do not edit baseline programs after seeing mutation outcomes.

Mutation set: exactly the 12 single-line transformations in mutations.json. Each must match its source anchor exactly once and compile. A compile failure is INVALID, not DETECTED. A baseline/reference failure makes the corresponding comparison VOID. A completed trace divergence is DETECTED; a mutant-only wall/step timeout is NONTERMINATING, separately counted; a completed equal trace is SURVIVED. Run the full baseline suite for every survivor. A first divergence is enough to establish detection, with its program, PC and trace retained.

Expected survivors: the JALR link mutation and dropped bit-zero mask may survive because the current random generator uses JALR with rd=x0 and aligned targets. This is a prediction, not a result. Other mutations are expected to be detected, but all outcomes must be reported.

Extended suite: add directed witnesses after recording the baseline mutation results. Witness requirements: JALR with a nonzero link register, odd target address, source/destination register aliasing, signed/unsigned boundaries, branch taken/not-taken for all six conditions, shift amounts 0/31 and masked register shifts, signed/unsigned byte/half loads at legal lanes, byte/half-store preservation, and writes to x0 followed by reads. Use the unchanged reference model; do not modify either model merely to make a mutant score improve.

Coverage: retain the existing instruction decoder. Measure retired mnemonics and per-branch taken/not-taken using actual consecutive retired PCs. Do not call either instruction or branch coverage proof of complete verification. Coverage over a suite stops at terminal ECALL/EBREAK; FENCE/CSRs, exceptions, misaligned accesses, interrupts, caches and pipelining are outside this core's supported scope.

Harness controls: two empty traces; equal truncated traces without termination; unequal trace lengths; malformed rows; missing trace; failed process; wall-clock timeout; instruction-limit exhaustion. Each must be rejected. An unmodified baseline must still complete and match, including a normal return through JALR.

Acceptance: every unmodified baseline and directed witness completes and matches; all 12 mutants have a status plus evidence; invalid/equivalent mutations are excluded and named; separately report baseline and extended detection counts. Do not promise a 12/12 result or retune the frozen set to achieve one. Preserve failed artifacts and stdout/stderr. No commits, pushes, or original home-checkout edits.
