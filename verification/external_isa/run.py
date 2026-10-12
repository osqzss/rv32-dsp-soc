"""GNU-assembled upstream tests, independent state reference, strict evidence gate."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "upstream/riscv-tests/isa"
BIN = ROOT / "tools/binutils/usr/bin/riscv64-unknown-elf-"
CORE = (ROOT / "project/rtl/rv32i_core.v" if (ROOT / "project").is_dir()
        else ROOT.parents[1] / "rtl/rv32i_core.v")
REF = ROOT / "upstream/rv32emu/build/rv32emu"


def command(args, log, env=None):
    with log.open("w") as out:
        subprocess.run([str(a) for a in args], stdout=out, stderr=subprocess.STDOUT,
                       check=True, timeout=30, env=env, cwd=ROOT)


def read_state(path):
    lines = path.read_text().splitlines()
    if len(lines) < 2 or not re.fullmatch(r"END [1-9][0-9]*", lines[-1]):
        raise ValueError(f"incomplete state: {path}")
    rows = []
    for line in lines[:-1]:
        if not re.fullmatch(r"[0-9a-f]{8}( [0-9a-f]{8}){33}", line):
            raise ValueError(f"malformed state: {path}")
        rows.append(tuple(int(x, 16) for x in line.split()))
    if int(lines[-1].split()[1]) != len(rows) or rows[0][0] != 0:
        raise ValueError("bad count or entry PC")
    if rows[0][2:] != (0,) * 32 or any(r[2] != 0 for r in rows):
        raise ValueError("bad initial registers or x0")
    if rows[-1][1] != 0x73 or any(r[1] == 0x73 for r in rows[:-1]):
        raise ValueError("bad terminal sentinel")
    return rows


def read_memory(path):
    lines = path.read_text().splitlines()
    if len(lines) != 4098 or lines[0] != "WORDS 4096" or lines[-1] != "END 4096":
        raise ValueError(f"incomplete memory: {path}")
    words = []
    for n, line in enumerate(lines[1:-1]):
        if not re.fullmatch(r"[0-9a-f]{8} [0-9a-f]{8}", line):
            raise ValueError("malformed memory")
        a, v = [int(x, 16) for x in line.split()]
        if a != 4*n:
            raise ValueError("bad memory address")
        words.append(v)
    return words


def compare(job):
    a, b = [read_state(job / f"{e}.state") for e in ("reference", "rtl")]
    for n, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            fields = [i for i, (u, v) in enumerate(zip(x, y)) if u != v]
            return dict(status="FAIL", kind="state", observation=n, fields=fields,
                        reference=x, rtl=y)
    if len(a) != len(b):
        return dict(status="FAIL", kind="length", reference=len(a), rtl=len(b))
    am, bm = [read_memory(job / f"{e}.memory") for e in ("reference", "rtl")]
    if am != bm:
        n = next(i for i, (x, y) in enumerate(zip(am, bm)) if x != y)
        return dict(status="FAIL", kind="memory", address=n*4, reference=am[n], rtl=bm[n])
    if a[-1][5] != 1:
        return dict(status="FAIL", kind="upstream_assertion", test_code=a[-1][5])
    return dict(status="PASS", instructions=len(a)-1, observations=len(a),
                registers_per_observation=32, words_compared=len(am), test_code=1)


def compile_test(name, job, source=None):
    source = source or TESTS / f"rv32ui/{name}.S"
    command(["gcc", "-E", "-P", "-x", "assembler-with-cpp", "-D__riscv_xlen=32",
             "-I", ROOT / "env", "-I", TESTS / "macros/scalar", source,
             "-o", job / "test.s"], job / "cpp.log")
    command([f"{BIN}as", "-march=rv32i", "-mabi=ilp32", "-mno-relax",
             job / "test.s", "-o", job / "test.o"], job / "as.log")
    command([f"{BIN}ld", "-m", "elf32lriscv", "--no-relax", "-T", ROOT / "env/link.ld",
             job / "test.o", "-o", job / "test.elf"], job / "ld.log")
    command([f"{BIN}objcopy", "-O", "binary", job / "test.elf", job / "test.bin"], job / "objcopy.log")
    data = (job / "test.bin").read_bytes()
    if len(data) > 16384:
        raise ValueError("image exceeds memory")
    data = data.ljust(16384, b"\0")
    (job / "test.hex").write_text("".join(f"{int.from_bytes(data[i:i+4], 'little'):08x}\n"
                                         for i in range(0, 16384, 4)))


def execute(name, job, sim, source=None):
    job.mkdir(parents=True, exist_ok=False)
    try:
        compile_test(name, job, source)
        env = dict(os.environ, RV32_VALIDATION_STATE=str(job / "reference.state"),
                   RV32_VALIDATION_MEMORY=str(job / "reference.memory"))
        command([REF, "-t", job / "test.elf"], job / "reference.log", env)
        command(["vvp", sim, f"+hex={job / 'test.hex'}", f"+state={job / 'rtl.state'}",
                 f"+memory={job / 'rtl.memory'}"], job / "rtl.log")
        result = compare(job)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = dict(status="ERROR", error=str(exc))
    result.update(name=name)
    (job / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def build(core, path):
    command(["iverilog", "-g2012", "-s", "tb_external", "-o", path,
             core, ROOT / "tb_external.sv"], path.with_suffix(".log"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--test")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sim = out / "baseline.sim"
    build(CORE, sim)
    manifest = json.loads((ROOT / "manifest.json").read_text()) if not args.test else [{"name": args.test}]
    results = []
    for test in manifest:
        if "unsupported" in test:
            row = dict(name=test["name"], status="UNSUPPORTED", reason=test["unsupported"])
        else:
            row = execute(test["name"], out / test["name"], sim)
        results.append(row)
        (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(row), flush=True)
    counts = {k: sum(r["status"] == k for r in results) for k in ("PASS", "FAIL", "UNSUPPORTED", "ERROR", "SKIPPED")}
    assert sum(counts.values()) == len(manifest)
    summary = dict(population=len(manifest), attempted=sum(counts[k] for k in ("PASS", "FAIL", "ERROR")),
                   counts=counts, instructions=sum(r.get("instructions", 0) for r in results),
                   results=results)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}))
    raise SystemExit(bool(counts["FAIL"] or counts["ERROR"]))
