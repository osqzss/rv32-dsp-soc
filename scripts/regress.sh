#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
exec python3 "$root/scripts/verify.py" regress "${1:-100}" "${2:-150}" \
  --out "${3:-$root/build/regress-$(date -u +%Y%m%dT%H%M%SZ)}"
