#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="$(dirname "$0")/prompt_city_night.txt"
OUTPUT_DIR="outputs/demo_city_night"

motifmaker init-from-prompt "$(cat "$PROMPT_FILE")" --out "$OUTPUT_DIR"

# Windows PowerShell 等价命令：
# $prompt = Get-Content examples/prompt_city_night.txt -Raw
# motifmaker init-from-prompt $prompt --out outputs/demo_city_night
