#!/usr/bin/env bash
# PreToolUse hook for Claude Code. Reads tool input JSON from stdin.
# If the matched Bash command is `git commit`, runs the dbt validators
# and exits 2 (with violations on stderr) when either fails.
# Bypass: append `--no-verify` to the commit, or set SKIP_DBT_CHECKS=1.

set -uo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get("tool_input", {}).get("command", ""))
')"

# Match `git commit` as a whole word, optionally followed by args.
if ! [[ "$command" =~ ^[[:space:]]*git[[:space:]]+commit([[:space:]]|$) ]]; then
    exit 0
fi

if [[ "$command" == *"--no-verify"* ]]; then
    echo "[dbt_pre_commit] --no-verify detected, skipping checks" >&2
    exit 0
fi

if [[ "${SKIP_DBT_CHECKS:-}" == "1" ]]; then
    echo "[dbt_pre_commit] SKIP_DBT_CHECKS=1, skipping checks" >&2
    exit 0
fi

# Run both validators, capturing combined output
combined=""
overall_status=0

if out1=$(python3 .claude/skills/validate-dbt-models/validate.py --quiet 2>&1); then
    :
else
    overall_status=1
    combined+="$out1"$'\n'
fi

if out2=$(python3 .claude/skills/enforce-naming-standards/validate.py --quiet 2>&1); then
    :
else
    overall_status=1
    if [[ -n "$combined" ]]; then
        combined+=$'\n'
    fi
    combined+="$out2"$'\n'
fi

if [[ $overall_status -eq 0 ]]; then
    exit 0
fi

# Block: emit violations and bypass hint on stderr, exit 2
{
    printf '%s' "$combined"
    echo
    echo "To bypass, re-run with \`git commit --no-verify\` or \`SKIP_DBT_CHECKS=1 git commit ...\` — only when intentional."
} >&2
exit 2
