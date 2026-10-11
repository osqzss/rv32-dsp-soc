"""Run the frozen single-fault study and retain every scored execution."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify import ROOT, ExecutionError, command, coverage, gen, read_trace, run_program, write_hex


def build(core, sim, log):
    command(["iverilog", "-g2005", "-s", "tb_core_verify", "-o", sim,
             core, ROOT / "tb/tb_core_verify.v"], log, timeout=600)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--no-directed", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    seals = json.loads((ROOT / "verification/seal.json").read_text())
    for name, expected in seals.items():
        actual = hashlib.sha256((ROOT / "verification" / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ExecutionError(f"frozen study changed: {name}")
    core = (ROOT / "rtl/rv32i_core.v").read_text()
    mutations = json.loads((ROOT / "verification/mutations.json").read_text())
    sim = out / "baseline.sim"
    command(["make", "iss"], out / "iss-build.log", timeout=600)
    build(ROOT / "rtl/rv32i_core.v", sim, out / "baseline-build.log")
    if args.baseline:
        previous = json.loads((args.baseline / "summary.json").read_text())
        if (previous["baseline_passed"] != 101 or len(previous["programs"]) != 101 or
                len(previous.get("mutations", [])) != len(mutations) or previous["seals"] != seals):
            raise ExecutionError("baseline study incomplete")
        programs = [] if args.no_directed else [{"name": "arch_edges", "source": (ROOT / "tests/arch_edges.s").read_text()}]
        # Reuse the exact original programs; never regenerate an altered baseline arm.
        for x in previous["programs"]:
            source = args.baseline / "programs" / (x["name"] + ".s")
            if hashlib.sha256(source.read_bytes()).hexdigest() != x["sha256"]:
                raise ExecutionError(f"baseline source hash mismatch: {x['name']}")
            programs.append({"name": x["name"], "source": source.read_text()})
    else:
        programs = [{"name": "smoke", "source": (ROOT / "tests/smoke.s").read_text()}]
        programs.extend({"name": f"seed_{i:03}", "source": gen(i, 300)} for i in range(1, 101))
    (out / "programs").mkdir()
    references = []
    for p in programs:
        source = out / "programs" / (p["name"] + ".s")
        source.write_text(p.pop("source"))
        p["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        p["hex"] = str(source.with_suffix(".hex"))
        write_hex(source.read_text(), p["hex"])
        result = run_program(p["hex"], sim, out / "baseline" / p["name"])
        if result["status"] != "PASS":
            raise ExecutionError(f"unmodified baseline diverged: {p['name']}")
        if p["name"] == "arch_edges":
            regs = [0] * 32
            for pc, insn, rd, value in read_trace(out / "baseline/arch_edges/iss.trace"):
                if rd:
                    regs[rd] = value
            expected = json.loads((ROOT / "tests/arch_edges.expected.json").read_text())
            for reg, value in expected.items():
                if regs[int(reg)] != value:
                    raise ExecutionError(f"independent directed oracle mismatch: x{reg}")
        references.append(out / "baseline" / p["name"] / "iss.trace")
        print(f"baseline {p['name']}: {result['instructions']} identical instructions", flush=True)
    report = {"phase": "extended" if args.baseline and not args.no_directed else "baseline", "seals": seals,
              "baseline_passed": len(programs), "programs": programs,
              "coverage": coverage(references), "mutations": []}
    save(out / "summary.json", report)
    for m in mutations:
        job = out / "mutations" / m["id"]
        job.mkdir(parents=True)
        if core.count(m["from"]) != 1:
            raise ExecutionError(f"mutation anchor not unique: {m['id']}")
        mutated = job / "rv32i_core.v"
        mutated.write_text(core.replace(m["from"], m["to"], 1))
        verdict = {"id": m["id"], "effect": m["effect"], "status": "SURVIVED", "programs_run": 0}
        try:
            build(mutated, job / "sim", job / "compile.log")
        except ExecutionError as exc:
            verdict.update(status="INVALID", detail=str(exc))
        else:
            for p in programs:
                verdict["programs_run"] += 1
                try:
                    result = run_program(p["hex"], job / "sim", job / p["name"])
                except ExecutionError as exc:
                    # Reference executions are unmodified and already passed above.
                    # Retain failures separately; they are never scored as trace detections.
                    verdict.update(status="EXECUTION_FAILURE", program=p["name"], detail=str(exc))
                    break
                if result["status"] == "DIFF":
                    verdict.update(status="DETECTED", program=p["name"], evidence=result)
                    break
        report["mutations"].append(verdict)
        save(out / "summary.json", report)
        print(f"{m['id']}: {verdict['status']} after {verdict['programs_run']} program(s)", flush=True)
    report["counts"] = {s: sum(x["status"] == s for x in report["mutations"])
                        for s in ("DETECTED", "SURVIVED", "INVALID", "EXECUTION_FAILURE")}
    save(out / "summary.json", report)
    print(json.dumps(report["counts"]))
    return int(report["counts"]["INVALID"] > 0 or report["counts"]["EXECUTION_FAILURE"] > 0)


if __name__ == "__main__":
    sys.exit(main())
