# Reference execution-mode correction

After first sealed full run: 42 manifest entries, 40 attempted, 39 PASS, 1 ERROR (reference SIGSEGV on jalr), 2 UNSUPPORTED, 0 FAIL/SKIPPED. Preserve runs/external-suite and logs/validation-v2.log. Earlier control setup failed on an incorrect development artifact path; logs/validation.log and runs/controls retained, corrected controls-v2 passed 10/10.

Cause: rv_step_debug constructs a stack instruction without the branch-history table allocated by normal block translation. rv32_template.c LOOKUP_OR_UPDATE_BRANCH_HISTORY_TABLE bypasses that table only when GDBSTUB is enabled and rv->debug_mode=true. The adapter did neither. This is incorrect adapter configuration, not a CPU divergence and not evidence of a reference ISA-semantics defect.

Correction: enable upstream GDBSTUB and set its debug_mode flag in the observation adapter before upstream rv_step_debug. Flush observations before stepping so process failures preserve their prefix. No upstream instruction semantics or RTL change. Rerun same jalr ELF input, then all controls and unchanged 42-entry manifest. Record new adapter patch/hash separately; original seal remains unchanged. Prediction: jalr completes, 40 supported tests pass. If it still fails, investigate rather than exclude it.
