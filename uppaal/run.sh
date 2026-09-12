#!/usr/bin/env bash
set -euo pipefail

MODEL_FILE="${1:-}"
OUTPUT_FILE="${2:-}"

$VERIFYTA_PATH --key $UPPAAL_LICENCE_KEY --lease 1 $MODEL_FILE > $OUTPUT_FILE
