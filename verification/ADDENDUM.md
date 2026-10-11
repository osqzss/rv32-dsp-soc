# Post-review instrumentation extension

Written after the original baseline and directed-arm runs, following Claude's independent review. PLAN.md and mutations.json remain sealed and unchanged. Preserve those historical results; do not relabel them using the new instrument.

Add optional final-memory snapshots to the C++ ISS and both RTL benches without changing ISA execution. Compare all 4,096 words in the standalone bench's 16 KB memory, represented by a required size header and sorted nonzero words. Missing, malformed or out-of-range snapshots fail. This catches stores even if software never reloads them.

Instrument revision v2 adds a required END record with the nonzero-word count so equal snapshots truncated at a complete-line boundary cannot pass. Historical v1 artifacts remain preserved. A real wrapper-level corruption control ensures Make's comparison entry point forwards the memory options. These changes follow code review and inspection, before the final proving run completes; no hypothesis or frozen mutation is altered.

For a faulty RTL run that fails to finish, report DETECTED only when two well-formed, nonempty traces have an actual differing row in their common prefix. Retain the noncompletion/error reason. An equal truncated prefix, missing output, malformed trace, compile failure or timeout without a proven divergence is not a detection or pass. A completed equal trace must also have successful processes, consistent halt counts and equal memory snapshots.

Rerun both arms with the same 101 saved baseline programs and unchanged 12 mutations. Keep these memory-aware results separate from the historical register-trace results. Also run each store mutant on all 100 random programs, with and without the memory comparison, to measure observability rather than extrapolate from the first detected program. Add a no-reload store witness and negative controls for memory corruption and incomplete divergent prefixes. Broader ISA coverage, independent third-party reference conformance, interrupts, misaligned traps, caches and pipelining remain out of scope.
