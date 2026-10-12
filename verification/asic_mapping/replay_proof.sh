#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v yosys >/dev/null
command -v yosys-abc >/dev/null
test ! -e runs/replay-proof
test ! -e runs/replay-normalized
mkdir -p runs/replay-normalized
python3 -B - <<'PY'
import gzip, hashlib, json
from pathlib import Path
root = Path.cwd()
p = json.loads((root / "artifacts/normalized/provenance.json").read_text())
cpu = (root / "../../rtl/rv32i_core.v").read_bytes().replace(b"\r\n", b"\n")
assert hashlib.sha256(cpu).hexdigest() == p["cpu_sha256"]
assert hashlib.sha256((root / "artifacts/netlists/repair.v").read_bytes()).hexdigest() == p["timed_repair_netlist_sha256"]
for arm, hashes in p["snapshots"].items():
    blob = (root / f"artifacts/normalized/{arm}.json.gz").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == hashes["public_gzip_sha256"]
    data = gzip.decompress(blob)
    assert hashlib.sha256(data).hexdigest() == hashes["public_json_sha256"]
    (root / f"runs/replay-normalized/{arm}.json").write_bytes(data)
PY
python3 -B state_miter_v5.py runs/replay-proof runs/replay-normalized
for variant in gold mapped mutant dflip swap deep; do
    cat > "runs/replay-proof/$variant.ys" <<EOF
read_json runs/replay-proof/$variant-pair.json
hierarchy -top gate
aigmap
opt_clean
check -assert
write_blif runs/replay-proof/$variant.blif
EOF
    timeout 30 yosys -s "runs/replay-proof/$variant.ys" > "runs/replay-proof/$variant-export.log" 2>&1
    timeout 150 yosys-abc -c "cec -T 120 runs/replay-proof/gold.blif runs/replay-proof/$variant.blif" > "runs/replay-proof/$variant-proof.log" 2>&1
    echo "$variant"
    grep 'Networks are' "runs/replay-proof/$variant-proof.log"
done
python3 -B audit_blif_v4.py runs/replay-proof
python3 -B - <<'PY'
import hashlib, json
from pathlib import Path
p = json.loads(Path("artifacts/normalized/provenance.json").read_text())
for arm, expected in p["expected_blif_sha256"].items():
    assert hashlib.sha256(Path(f"runs/replay-proof/{arm}.blif").read_bytes()).hexdigest() == expected, arm
print("SIX REPLAY BLIFS BYTE-IDENTICAL TO RECORDED PROOF INPUTS")
PY
echo 'PUBLIC MAPPING PROOF REPLAY PASS'
