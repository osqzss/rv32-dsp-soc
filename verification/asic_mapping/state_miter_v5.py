"""Expose all matching flops for a complete combinational induction step."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = Path(sys.argv[2]).resolve()
assert RUN.parent == (ROOT / "runs").resolve(), RUN
OUT = Path(sys.argv[1]).resolve()
assert OUT.parent == (ROOT / "runs").resolve() and not OUT.exists(), OUT
OUT.mkdir()
STATES = ["imem_addr", "halted"] + [f"regs[{i}]" for i in range(1, 32)]
ALLOWED = {"$_AND_", "$_OR_", "$_NOT_", "$_XOR_", "$_MUX_"}


def expose(arm, mutation=None):
    m = json.loads((RUN / f"{arm}.json").read_text())["modules"]["rv32i_core"]
    if mutation == "swap":
        bits = m["netnames"]["regs[1]"]["bits"]
        bits[0], bits[1] = bits[1], bits[0]
    if mutation == "dflip":
        q = m["netnames"]["regs[1]"]["bits"][0]
        targets = [c for c in m["cells"].values() if c["type"] == "$_DFF_PN0_" and c["connections"]["Q"] == [q]]
        assert len(targets) == 1
        d = targets[0]["connections"]["D"]
        new = max(b for v in m["netnames"].values() for b in v["bits"] if isinstance(b, int)) + 1
        m["cells"]["mutation_register_d"] = {
            "type": "$_NOT_", "parameters": {}, "attributes": {},
            "port_directions": {"A": "input", "Y": "output"}, "connections": {"A": d, "Y": [new]}}
        m["netnames"]["mutation_register_d_wire"] = {"hide_name": 0, "bits": [new], "attributes": {}}
        targets[0]["connections"]["D"] = [new]
    q_to_ff = {}
    for name, cell in m["cells"].items():
        if cell["type"] == "$scopeinfo":
            continue
        if cell["type"] == "$_DFF_PN0_":
            p = cell["connections"]
            assert p["C"] == m["ports"]["clk"]["bits"], (arm, name, "clock")
            assert p["R"] == m["ports"]["rst_n"]["bits"], (arm, name, "reset")
            assert len(p["Q"]) == len(p["D"]) == 1
            assert p["Q"][0] not in q_to_ff
            q_to_ff[p["Q"][0]] = (name, p["D"][0])
        else:
            assert cell["type"] in ALLOWED, (arm, name, cell["type"])
    state_bits = [b for n in STATES for b in m["netnames"][n]["bits"]]
    assert len(state_bits) == len(set(state_bits)) == len(q_to_ff) == 1025
    assert set(state_bits) == set(q_to_ff), (arm, "unmatched state")
    next_bit = max(b for n in m["netnames"].values() for b in n["bits"] if isinstance(b, int)) + 1
    for i, n in enumerate(STATES):
        bits = m["netnames"][n]["bits"]
        m["ports"][f"state_{i}"] = {"direction": "input", "bits": bits}
        ds = []
        for q in bits:
            name, d = q_to_ff[q]
            del m["cells"][name]
            y = next_bit
            next_bit += 1
            m["cells"][f"reset_next_{y}"] = {
                "type": "$_MUX_", "parameters": {}, "attributes": {},
                "port_directions": {"A": "input", "B": "input", "S": "input", "Y": "output"},
                "connections": {"A": ["0"], "B": [d], "S": m["ports"]["rst_n"]["bits"], "Y": [y]},
            }
            ds.append(y)
        m["ports"][f"next_{i}"] = {"direction": "output", "bits": ds}
    m["cells"] = {n: c for n, c in m["cells"].items() if c["type"] != "$scopeinfo"}
    return m


gold, gate = expose("gold"), expose("gate")
unknowns = [(c, p, i) for c in gold["cells"].values() for p, bs in c["connections"].items()
            for i, b in enumerate(bs) if b in ("x", "z")]
assert len(unknowns) > 0, len(unknowns)
for j, (cell, port, index) in enumerate(unknowns):
    assert cell["port_directions"][port] == "input"
    for arm in (gold, gate):
        bit = max(b for c in arm["cells"].values() for bs in c["connections"].values()
                  for b in bs if isinstance(b, int)) + 1
        bit = max(bit, max(b for p in arm["ports"].values() for b in p["bits"] if isinstance(b, int)) + 1)
        bit = max(bit, max(b for p in arm["netnames"].values() for b in p["bits"] if isinstance(b, int)) + 1)
        arm["ports"][f"undef_{j}"] = {"direction": "input", "bits": [bit]}
        if arm is gold:
            cell["connections"][port][index] = bit
assert {n: (p["direction"], len(p["bits"])) for n, p in gold["ports"].items()} == {
    n: (p["direction"], len(p["bits"])) for n, p in gate["ports"].items()}
for variant in ("gold", "mapped", "mutant", "dflip", "swap", "deep"):
    out = OUT / f"{variant}-pair.json"
    assert not out.exists(), out
    g = copy.deepcopy(gold if variant == "gold" else gate) if variant in ("gold", "mapped", "mutant") else expose("deep" if variant == "deep" else "gate", None if variant == "deep" else variant)
    for n, p in gold["ports"].items():
        if n.startswith("undef_") and n not in g["ports"]:
            bit = max(b for v in g["netnames"].values() for b in v["bits"] if isinstance(b, int)) + 1
            bit = max(bit, max(b for v in g["cells"].values() for bs in v["connections"].values() for b in bs if isinstance(b, int)) + 1)
            bit = max(bit, max(b for v in g["ports"].values() for b in v["bits"] if isinstance(b, int)) + 1)
            g["ports"][n] = {"direction": "input", "bits": [bit]}
    if variant == "mutant":
        # Change the real mapped retire write-enable output, preserving its internal fanout.
        old = g["ports"]["retire_we"]["bits"]
        new = max(b for p in g["ports"].values() for b in p["bits"] if isinstance(b, int)) + 1
        new = max(new, max(b for c in g["cells"].values() for p in c["connections"].values() for b in p if isinstance(b, int)) + 1)
        g["cells"]["mutation_retire_we"] = {
            "type": "$_NOT_", "parameters": {}, "attributes": {},
            "port_directions": {"A": "input", "Y": "output"},
            "connections": {"A": old, "Y": [new]},
        }
        g["ports"]["retire_we"]["bits"] = [new]
        g["netnames"]["retire_we"]["bits"] = [new]
    for m in (gold, g):
        for n, p in m["ports"].items():
            if n not in m["netnames"]:
                m["netnames"][n] = {"hide_name": 0, "bits": p["bits"], "attributes": {}}
            assert m["netnames"][n]["bits"] == p["bits"], (variant, n, "port/net alias")
    out.write_text(json.dumps({"modules": {"gold": gold, "gate": g}}), encoding="ascii")
print("STATE AUDIT PASS: 1025 matching positive-edge, active-low asynchronous-zero-reset flops per arm; no other state or unsupported cells")
print("PROOF OUTPUTS: all original output ports and all 1025 next-state bits; unrestricted common current state and external inputs")
print(f"UNDEFINED VALUES: {len(unknowns)} prep-gold mux defaults replaced by independent unrestricted inputs; matching gate inputs unused")
(OUT / "interface.json").write_text(json.dumps({"inputs": 1091 + len(unknowns), "outputs": 1229, "symbolic_unknowns": len(unknowns)}), encoding="ascii")
