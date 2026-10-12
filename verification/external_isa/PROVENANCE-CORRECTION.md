# Upstream revision labels corrected

The source-probe output printed two unlabeled revisions in alphabetical folder order (riscv-tests, then rv32emu). The author transposed them in PLAN.md and subsequent prose. Direct git remote get-url origin and git rev-parse HEAD establish:

| Origin | Actual tested revision |
|---|---|
| https://github.com/sysprog21/rv32emu.git | a5b5f9217fb2b4d8a73fcf4e572aa90ccc33f07c |
| https://github.com/riscv-software-src/riscv-tests.git | 7b68f7b91f827f8d94cc1c57ff123752c5c8f704 |

These are the same on-disk sources used for every recorded test. No checkout, source/test file, manifest hash, metric or exclusion changed in this correction. Original PLAN.md/plan-seal.sha256/seal.json/seal-v2.sha256 remain unchanged as historical records; this correction supersedes only their mislabeled origin-to-revision mapping. Mutable RESULTS.md, HANDOFF.md and portable bootstrap pins corrected. New provenance.json is generated directly from each named repository rather than positional output.

Tool-version correction from finish_evidence.sh output: Icarus and vvp 14.0 development build s20260301-322-ga4989d023-dirty, not 13.0. No tool was changed. Native gcc/g++13.3, Python3.12.3, binutils2.42 and Make4.3 confirmed.
