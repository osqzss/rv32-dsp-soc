"""Real engine mutations and evidence corruption must fail for the named reason."""
import json
import shutil
import sys
from pathlib import Path

from run import ROOT, CORE, build, compare, execute

out = (ROOT / sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
rows = []
baseline = out / "baseline.sim"
build(CORE, baseline)

for name, test, old, new, allowed in [
    ("sra_logical", "sra", "if (alt) alu_out = $signed(a) >>> shamt;", "if (alt) alu_out = a >> shamt;", "state"),
    ("beq_inverted", "beq", "branch_taken = (a == b);", "branch_taken = (a != b);", "state"),
    ("sb_lane0", "sb", "st_strb = 4'b0001 << byte_off;", "st_strb = 4'b0001;", "state"),
]:
    text = CORE.read_text()
    assert text.count(old) == 1
    core = out / (name + ".v")
    core.write_text(text.replace(old, new))
    sim = out / (name + ".sim")
    build(core, sim)
    result = execute(test, out / name, sim)
    assert result["status"] == "FAIL" and result["kind"] == allowed, result
    rows.append(dict(control=name, **result))

# Change an upstream expected result, not an engine. Both must take the fail path.
src = (ROOT / "upstream/riscv-tests/isa/rv64ui/add.S").read_text()
old = "TEST_RR_OP( 3,  add, 0x00000002,"
assert src.count(old) == 1
source = out / "bad_expected.S"
source.write_text(src.replace(old, "TEST_RR_OP( 3,  add, 0x00000003,"))
result = execute("add", out / "bad_expected", baseline, source)
assert result["status"] == "FAIL" and result["kind"] == "upstream_assertion", result
rows.append(dict(control="wrong_upstream_expected", **result))

good = ROOT / "runs/development-add/add"
for name, filename, transform, kind in [
    ("register", "rtl.state", lambda s: s.replace("00000002", "00000003", 1), "state"),
    ("pc", "rtl.state", lambda s: s.replace("00000004 ", "00000008 ", 1), "state"),
    ("memory", "rtl.memory", lambda s: s.replace("00003ffc 00000000", "00003ffc 00000001"), "memory"),
    ("truncated", "rtl.state", lambda s: s[:s.rfind("END")], "invalid"),
    ("empty", "rtl.state", lambda s: "", "invalid"),
]:
    job = out / ("corrupt_" + name)
    job.mkdir()
    for filename0 in ("reference.state", "rtl.state", "reference.memory", "rtl.memory"):
        shutil.copyfile(good / filename0, job / filename0)
    path = job / filename
    old = path.read_text()
    changed = transform(old)
    assert changed != old
    path.write_text(changed)
    try:
        result = compare(job)
        assert result["status"] == "FAIL" and result["kind"] == kind, result
    except ValueError as exc:
        assert kind == "invalid"
        result = dict(status="REJECTED", kind="invalid", error=str(exc))
    rows.append(dict(control="corrupt_" + name, **result))

result = execute("add", out / "baseline_after_controls", baseline)
assert result["status"] == "PASS", result
rows.append(dict(control="unchanged_after_controls", **result))
(out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(dict(controls_passed=len(rows), controls=[{k:v for k,v in r.items()
    if k not in ("reference", "rtl")} for r in rows]), indent=2))
