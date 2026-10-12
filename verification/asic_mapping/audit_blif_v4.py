"""Check proof-interface identity and whether ABC's undriven nets affect outputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = Path(sys.argv[1]).resolve()
assert RUN.parent == (ROOT / "runs").resolve(), RUN
interface = json.loads((RUN / "interface.json").read_text())


def inspect(path):
    ins, outs, fanin = set(), set(), {}
    for line in path.read_text().replace("\\\n", " ").splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == ".inputs":
            ins.update(words[1:])
        elif words[0] == ".outputs":
            outs.update(words[1:])
        elif words[0] == ".names":
            assert words[-1] not in fanin, (path, "multiple drivers", words[-1])
            fanin[words[-1]] = words[1:-1]
        elif words[0] in (".subckt", ".gate", ".latch"):
            raise AssertionError((path, "non-combinational/unexpanded cell", words))
    reachable, todo = set(), list(outs)
    while todo:
        node = todo.pop()
        if node not in reachable:
            reachable.add(node)
            todo.extend(fanin.get(node, []))
    missing = {p for ps in fanin.values() for p in ps} - set(fanin) - ins
    assert not (missing & reachable), (path, "undriven proof cone", missing & reachable)
    assert "$undef" not in reachable, (path, "undefined proof cone")
    assert len(ins) == interface["inputs"] and len(outs) == interface["outputs"], (path, len(ins), len(outs))
    print(path.name, "inputs", len(ins), "outputs", len(outs), "undriven outside output cone", len(missing))
    return ins, outs, {"inputs": len(ins), "outputs": len(outs), "undriven_outside_cone": sorted(missing)}


reference = None
report = {}
for arm in ("gold", "mapped", "mutant", "dflip", "swap", "deep"):
    ins, outs, result = inspect(RUN / f"{arm}.blif")
    if reference is None:
        reference = (ins, outs)
    assert reference == (ins, outs), (arm, "proof interface mismatch")
    log = (RUN / f"{arm}-proof.log").read_text()
    if arm in ("mutant", "dflip", "swap", "deep"):
        assert "Networks are NOT EQUIVALENT" in log
        if arm == "mutant":
            assert "Output retire_we:" in log
        elif arm == "dflip":
            assert "Output next_2[0]:" in log and "rst_n = 1'h1" in log
        elif arm == "swap":
            assert "Verification failed for at least 2 outputs:  dmem_wstrb[1] dmem_wstrb[2]" in log
        else:
            assert "Verification failed for at least 4 outputs:  dmem_wdata[15] dmem_wdata[23] dmem_wdata[31]" in log
    else:
        assert "Networks are equivalent" in log and "NOT EQUIVALENT" not in log
    report[arm] = result
out = RUN / "AUDIT.json"
if out.exists():
    assert json.loads(out.read_text()) == report, "existing audit changed"
else:
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
print("BLIF CONE AND PROOF AUDIT PASS")
