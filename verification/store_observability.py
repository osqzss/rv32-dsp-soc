"""Paired comparison of trace-only and memory-aware store observability."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify import compare, run_program

out = ROOT / "build/store-observability-v2"
out.mkdir(parents=True, exist_ok=False)
results = {}
for mutant in ("sb_lane0", "sh_swapped_lanes"):
    rows = []
    for seed in range(1, 101):
        name = f"seed_{seed:03}"
        job = out / mutant / name
        combined = run_program(ROOT / f"build/study-memory-v2-extended/programs/{name}.hex",
                               ROOT / f"build/study-memory-v2-extended/mutations/{mutant}/sim", job)
        trace = compare(job / "iss.trace", job / "rtl.trace")
        rows.append({"seed": seed, "trace_only": trace["status"], "combined": combined["status"],
                     "detected_by": combined.get("kind")})
    results[mutant] = {"programs": 100, "trace_only_detected": sum(r["trace_only"] == "DIFF" for r in rows),
                       "combined_detected": sum(r["combined"] == "DIFF" for r in rows), "rows": rows}
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(mutant, {k: v for k, v in results[mutant].items() if k != "rows"}, flush=True)
