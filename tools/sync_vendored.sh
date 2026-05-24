#!/usr/bin/env bash
# Copy the canonical tools/search.py into every skill's scripts/search.py.
# Run from anywhere; paths are resolved relative to this script.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$here")"
src="$here/search.py"
count=0
for skill_scripts in "$root"/skills/*/scripts; do
  [ -d "$skill_scripts" ] || continue
  cp "$src" "$skill_scripts/search.py"
  echo "synced -> ${skill_scripts#"$root"/}/search.py"
  count=$((count + 1))
done
echo "synced $count vendored copy/copies from tools/search.py"
