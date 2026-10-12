"""Additional controls for memory-only faults and equal incomplete evidence."""
import json
import shutil
from run import ROOT, CORE, build, execute, compare

out = ROOT / "runs/extra-controls"
out.mkdir(parents=True, exist_ok=False)
baseline = out / "baseline.sim"
build(CORE, baseline)
source = out / "no_reload.S"
source.write_text(".globl _start\n_start:\nli x31, 0x2000\nli x5, 0x55\nsb x5, 1(x31)\nli x3, 1\necall\n")
gold = execute("no_reload", out / "gold", baseline, source)
assert gold["status"] == "PASS", gold
text = CORE.read_text()
old = "st_strb = 4'b0001 << byte_off;"
assert text.count(old) == 1
core = out / "sb_lane0.v"
core.write_text(text.replace(old, "st_strb = 4'b0001;"))
sim = out / "sb_lane0.sim"
build(core, sim)
bad = execute("no_reload", out / "mutant", sim, source)
assert bad["status"] == "FAIL" and bad["kind"] == "memory", bad
assert (out / "mutant/rtl.state").read_bytes() == (out / "mutant/reference.state").read_bytes()
results = [dict(control="memory_only_gold", **gold), dict(control="memory_only_store_mutant", **bad)]
for kind in ("empty", "truncated", "memory_truncated"):
    job = out / kind
    job.mkdir()
    for name in ("reference.state", "rtl.state", "reference.memory", "rtl.memory"):
        shutil.copyfile(out / "gold" / name, job / name)
    for engine in ("reference", "rtl"):
        path = job / (engine + (".memory" if kind == "memory_truncated" else ".state"))
        s = path.read_text()
        path.write_text("" if kind == "empty" else s[:s.rfind("END")])
    try:
        compare(job)
    except ValueError as exc:
        results.append(dict(control="equal_" + kind, status="REJECTED", error=str(exc)))
    else:
        raise AssertionError("equal incomplete evidence accepted")
(out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(dict(controls_passed=len(results), results=results), indent=2))
