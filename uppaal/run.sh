#!/usr/bin/env bash
set -euo pipefail

KEY="${1:-}"
MODEL_FILE="${2:-}"
OUTPUT_FILE="${3:-}"

$VERIFYTA_PATH --key $KEY --lease 1 $MODEL_FILE > $OUTPUT_FILE
