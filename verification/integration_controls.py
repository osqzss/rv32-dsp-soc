"""Real-process controls for instruction exhaustion and sealed source reuse."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify import ExecutionError, command, compare, read_trace, run_program, write_hex


def main():
    out = ROOT / "build/integration-controls-memory-v2"
    out.mkdir(parents=True, exist_ok=False)
    expected = json.loads((ROOT / "tests/arch_edges.expected.json").read_text())
    for engine in ("iss", "rtl"):
        regs = [0] * 32
        for pc, insn, rd, value in read_trace(ROOT / f"build/study-memory-v2-extended/baseline/arch_edges/{engine}.trace"):
            if rd:
                regs[rd] = value
        assert all(regs[int(r)] == v for r, v in expected.items()), engine
    print("PASS: independent directed register oracle matches ISS and RTL, including all jump links")
    infinite = out / "infinite.hex"
    write_hex("loop: jal x0, loop\n", infinite)
    try:
        run_program(infinite, ROOT / "build/study-memory-v2-extended/baseline.sim",
                    out / "instruction-limit", max_steps=10)
    except ExecutionError as exc:
        assert "incomplete execution" in str(exc), str(exc)
        assert len((out / "instruction-limit/iss.trace").read_text().splitlines()) == 10
        print("PASS: real ISS instruction limit rejected before RTL scoring")
    else:
        raise AssertionError("instruction exhaustion accepted")
    try:
        command(["vvp", ROOT / "build/study-memory-v2-extended/baseline.sim",
                 f"+hex={infinite}", f"+trace={out / 'limited-rtl.trace'}",
                 f"+memory={out / 'limited-rtl.memory'}", "+max=10"],
                out / "limited-rtl.log")
    except ExecutionError:
        assert "instruction limit reached" in (out / "limited-rtl.log").read_text()
        print("PASS: real RTL instruction limit exits nonzero")
    else:
        raise AssertionError("RTL instruction exhaustion accepted")
    baseline = out / "tampered-baseline"
    (baseline / "programs").mkdir(parents=True)
    shutil.copyfile(ROOT / "build/study-baseline/summary.json", baseline / "summary.json")
    (baseline / "programs/smoke.s").write_text("ecall\n")
    try:
        command([sys.executable, ROOT / "verification/study.py", "--out", out / "tamper-run",
                 "--baseline", baseline], out / "tamper.log", timeout=600)
    except ExecutionError:
        assert "baseline source hash mismatch: smoke" in (out / "tamper.log").read_text()
        assert not (out / "tamper-run/summary.json").exists()
        print("PASS: tampered baseline rejected before scoring")
    else:
        raise AssertionError("changed baseline source accepted")
    result = run_program(ROOT / "build/study-memory-v2-extended/programs/smoke.hex",
                         ROOT / "build/study-memory-v2-extended/mutations/jal_link_plus8/sim",
                         out / "divergent-nonterminating", max_steps=200)
    assert result["status"] == "DIFF" and result["first_divergence"] == 57
    assert result["rtl_completed"] is False and result["rtl_execution_failure"]
    print("PASS: real divergent, nonterminating RTL detected at retire row 57; failure retained")
    stores = out / "no-reload.hex"
    write_hex("li x31, 0x2000\nli x1, 0x12345678\nsw x1, 0(x31)\nli x2, 0x55\nsb x2, 1(x31)\nsh x1, 2(x31)\necall\n", stores)
    for mutant in ("sb_lane0", "sh_swapped_lanes"):
        job = out / mutant
        result = run_program(stores, ROOT / f"build/study-memory-v2-extended/mutations/{mutant}/sim", job)
        assert compare(job / "iss.trace", job / "rtl.trace")["status"] == "PASS"
        assert result["status"] == "DIFF" and result["kind"] == "memory"
        print(f"PASS: {mutant} detected in memory despite identical complete retire traces")
    (out / "changed.memory").write_text("WORDS 4096\nEND 0\n")
    gold = ROOT / "build/study-memory-v2-extended/baseline/arch_edges"
    try:
        command(["bash", ROOT / "scripts/compare.sh", gold / "iss.trace", gold / "rtl.trace",
                 "--iss-memory", gold / "iss.memory", "--rtl-memory", out / "changed.memory"],
                out / "wrapper-memory.log")
    except ExecutionError:
        result = json.loads((out / "wrapper-memory.log").read_text())
        assert result["status"] == "DIFF" and result["kind"] == "memory"
        print("PASS: shell comparison wrapper forwards memory paths and rejects corruption")
    else:
        raise AssertionError("wrapper dropped memory comparison")
    (out / "result.json").write_text(json.dumps({"controls_passed": 8}) + "\n")


if __name__ == "__main__":
    main()
