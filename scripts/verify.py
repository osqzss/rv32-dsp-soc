"""Complete, independently scored CPU executions; no empty-trace passes."""
import argparse
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model"))
from asm import assemble
from gen_random import gen
from coverage import decode, RV32I, BRANCH


class ExecutionError(Exception):
    pass


def read_trace(path, complete=True):
    rows = []
    with Path(path).open() as stream:
        for n, line in enumerate(stream, 1):
            fields = line.split()
            if (len(fields) != 4 or any(not re.fullmatch(r"[0-9a-fA-F]{8}", fields[i])
                                       for i in (0, 1, 3)) or
                    not re.fullmatch(r"\d+", fields[2]) or not 0 <= int(fields[2]) < 32):
                raise ExecutionError(f"{path}:{n}: malformed trace")
            rows.append((int(fields[0], 16), int(fields[1], 16),
                         int(fields[2]), int(fields[3], 16)))
    if not rows or rows[0][0] != 0 or (complete and rows[-1][1] & 0x7f != 0x73):
        raise ExecutionError(f"{path}: empty or incomplete execution")
    if any(row[1] & 0x7f == 0x73 for row in rows[:-1]):
        raise ExecutionError(f"{path}: instructions after termination")
    return rows


def compare(iss_path, rtl_path):
    iss, rtl = read_trace(iss_path), read_trace(rtl_path)
    return compare_rows(iss, rtl)


def compare_rows(iss, rtl, prefix=False):
    pairs = zip(iss, rtl) if prefix else itertools.zip_longest(iss, rtl)
    for n, (a, b) in enumerate(pairs, 1):
        if a != b:
            return {"status": "DIFF", "first_divergence": n,
                    "iss": a, "rtl": b, "iss_instructions": len(iss),
                    "rtl_instructions": len(rtl)}
    return {"status": "PASS", "instructions": len(iss)}


def read_memory(path):
    lines = Path(path).read_text().splitlines()
    if not lines or not re.fullmatch(r"WORDS 4096", lines[0]):
        raise ExecutionError(f"{path}: missing or invalid memory size")
    if len(lines) < 2 or not re.fullmatch(r"END \d+", lines[-1]):
        raise ExecutionError(f"{path}: incomplete memory snapshot")
    words = {}
    previous = -1
    for line in lines[1:-1]:
        if not re.fullmatch(r"[0-9a-fA-F]{8} [0-9a-fA-F]{8}", line):
            raise ExecutionError(f"{path}: malformed memory word")
        addr, value = (int(v, 16) for v in line.split())
        if addr % 4 or not previous < addr < 16384 or value == 0:
            raise ExecutionError(f"{path}: invalid memory address/order/value")
        words[addr] = value
        previous = addr
    if int(lines[-1].split()[1]) != len(words):
        raise ExecutionError(f"{path}: memory word count mismatch")
    return words


def compare_memory(iss_path, rtl_path):
    iss, rtl = read_memory(iss_path), read_memory(rtl_path)
    for addr in sorted(iss.keys() | rtl.keys()):
        if iss.get(addr, 0) != rtl.get(addr, 0):
            return {"status": "DIFF", "kind": "memory", "address": addr,
                    "iss": iss.get(addr, 0), "rtl": rtl.get(addr, 0)}
    return {"status": "PASS", "words_compared": 4096}


def command(args, log, timeout=60):
    try:
        with Path(log).open("w") as output:
            result = subprocess.run([str(x) for x in args], cwd=ROOT,
                                    stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ExecutionError(f"wall timeout: {log}") from exc
    except OSError as exc:
        raise ExecutionError(f"process launch failed: {exc}") from exc
    if result.returncode:
        raise ExecutionError(f"process exit {result.returncode}: {log}")


def run_program(hex_path, sim, out, max_steps=5000, timeout=60):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    iss, rtl = out / "iss.trace", out / "rtl.trace"
    command([ROOT / "build/iss", hex_path, iss, max_steps, out / "iss.memory", 4096],
            out / "iss.log", timeout)
    reference = read_trace(iss)
    read_memory(out / "iss.memory")
    text = (out / "iss.log").read_text()
    if not re.search(rf"ISS: retired {len(reference)} instruction\(s\), halted", text):
        raise ExecutionError("ISS completion count missing or inconsistent")
    failure = None
    try:
        command(["vvp", sim, f"+hex={hex_path}", f"+trace={rtl}",
                 f"+memory={out / 'rtl.memory'}", f"+max={max_steps}"], out / "rtl.log", timeout)
    except ExecutionError as exc:
        failure = str(exc)
    actual = read_trace(rtl, complete=False)
    prefix = compare_rows(reference, actual, prefix=True)
    if prefix["status"] == "DIFF":
        prefix.update(kind="trace", rtl_execution_failure=failure,
                      rtl_completed=bool(actual[-1][1] & 0x7f == 0x73 and failure is None))
        (out / "result.json").write_text(json.dumps(prefix, indent=2) + "\n")
        return prefix
    if failure:
        raise ExecutionError(failure)
    read_trace(rtl)
    text = (out / "rtl.log").read_text()
    if not re.search(rf"RTL: retired {len(actual)} instruction\(s\).*halted", text):
        raise ExecutionError("RTL completion count missing or inconsistent")
    result = compare(iss, rtl)
    if result["status"] == "PASS":
        memory = compare_memory(out / "iss.memory", out / "rtl.memory")
        result = memory if memory["status"] == "DIFF" else {**result, **memory}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def write_hex(source, path):
    words = assemble(source)
    Path(path).write_text("".join(f"{w & 0xffffffff:08x}\n" for w in words))


def coverage(paths):
    counts = {name: 0 for name in RV32I}
    branches = {name: {"taken": 0, "not_taken": 0, "ambiguous": 0}
                for name in BRANCH.values()}
    total = 0
    for path in paths:
        rows = read_trace(path)
        total += len(rows)
        for i, (pc, insn, rd, value) in enumerate(rows):
            name = decode(insn)
            if name in counts:
                counts[name] += 1
            if name in branches and i + 1 < len(rows):
                off = (((insn >> 31) & 1) << 12 | ((insn >> 7) & 1) << 11 |
                       ((insn >> 25) & 0x3f) << 5 | ((insn >> 8) & 0xf) << 1)
                next_pc = rows[i + 1][0]
                outcome = "ambiguous" if off == 4 else (
                    "not_taken" if next_pc == (pc + 4) & 0xffffffff else "taken")
                branches[name][outcome] += 1
    return {"programs": len(paths), "retired_instructions": total,
            "instruction_counts": counts, "mnemonics_hit": sum(v > 0 for v in counts.values()),
            "mnemonics_total": len(counts), "branch_outcomes": branches,
            "branch_bins_hit": sum(v[k] > 0 for v in branches.values()
                                   for k in ("taken", "not_taken")), "branch_bins_total": 12}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    comp = sub.add_parser("compare")
    comp.add_argument("iss", type=Path)
    comp.add_argument("rtl", type=Path)
    comp.add_argument("--iss-memory", type=Path)
    comp.add_argument("--rtl-memory", type=Path)
    reg = sub.add_parser("regress")
    reg.add_argument("seeds", type=int)
    reg.add_argument("body", type=int)
    reg.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "compare":
            result = compare(args.iss, args.rtl)
            if bool(args.iss_memory) != bool(args.rtl_memory):
                raise ExecutionError("both memory paths required")
            if result["status"] == "PASS" and args.iss_memory:
                memory = compare_memory(args.iss_memory, args.rtl_memory)
                result = memory if memory["status"] == "DIFF" else {**result, **memory}
            print(json.dumps(result))
            return 0 if result["status"] == "PASS" else 1
        if args.seeds < 1 or args.body < 1:
            parser.error("seeds and body must be positive")
        args.out = args.out.resolve()
        args.out.mkdir(parents=True, exist_ok=False)
        command(["make", "iss", "sim"], args.out / "build.log", timeout=600)
        rows, traces = [], []
        for seed in range(1, args.seeds + 1):
            source = args.out / f"r{seed}.s"
            source.write_text(gen(seed, args.body))
            hex_path = source.with_suffix(".hex")
            write_hex(source.read_text(), hex_path)
            result = run_program(hex_path, ROOT / "build/sim", args.out / f"r{seed}")
            rows.append({"seed": seed, **result})
            (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
            if result["status"] != "PASS":
                print(json.dumps(rows[-1]))
                return 1
            traces.append(args.out / f"r{seed}/iss.trace")
            print(f"seed {seed}: PASS, {result['instructions']} retired", flush=True)
        stats = coverage(traces)
        (args.out / "coverage.json").write_text(json.dumps(stats, indent=2) + "\n")
        print(json.dumps(stats))
        return 0
    except (ExecutionError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
