#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:-build/demo-$(date +%Y%m%d-%H%M%S)}"

python -m datagate inspect examples/incoming_customers.csv --out "$OUT/incoming"
python -m datagate compare examples/baseline.profile.json "$OUT/incoming/profile.json" --out "$OUT/drift"

set +e
python -m datagate validate examples/incoming_customers.csv \
  --contract examples/customers.contract.json \
  --out "$OUT/validation"
validation_status=$?
set -e
if [ "$validation_status" -eq 1 ]; then
  echo "Expected: the synthetic sample contains contract violations."
elif [ "$validation_status" -ne 0 ]; then
  echo "DataGate validation failed operationally (exit $validation_status)." >&2
  exit "$validation_status"
fi

python -m datagate clean examples/incoming_customers.csv \
  --contract examples/customers.contract.json \
  --out "$OUT/cleaned_customers.csv"

echo
echo "Demo artifacts: $OUT"
echo "Open $OUT/incoming/report.html, $OUT/drift/report.html, and $OUT/validation/report.html."
