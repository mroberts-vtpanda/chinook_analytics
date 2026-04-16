#!/usr/bin/env bash
# End-to-end smoke test: runs both validators against the real repo,
# then exercises the hook handler with the four scenarios it must handle.

set -uo pipefail

cd "$(git rev-parse --show-toplevel)"

assert_exit() {
    local expected="$1" actual="$2" label="$3"
    if [[ "$actual" -ne "$expected" ]]; then
        echo "FAIL: $label — expected exit $expected, got $actual" >&2
        exit 1
    fi
    echo "ok: $label (exit $actual)"
}

# 1. Real repo passes both validators
python3 .claude/skills/validate-dbt-models/validate.py --quiet
assert_exit 0 $? "validate-dbt-models on real repo"
python3 .claude/skills/enforce-naming-standards/validate.py --quiet
assert_exit 0 $? "enforce-naming-standards on real repo"

# 2. Hook lets non-commit calls through
echo '{"tool_input":{"command":"git status"}}' | .claude/hooks/dbt_pre_commit.sh
assert_exit 0 $? "hook lets git status through"

# 3. Hook lets clean commit through
echo '{"tool_input":{"command":"git commit -m test"}}' | .claude/hooks/dbt_pre_commit.sh
assert_exit 0 $? "hook lets clean git commit through"

# 4. --no-verify bypass
echo '{"tool_input":{"command":"git commit --no-verify -m test"}}' | .claude/hooks/dbt_pre_commit.sh 2>/dev/null
assert_exit 0 $? "--no-verify bypass"

# 5. SKIP_DBT_CHECKS bypass
SKIP_DBT_CHECKS=1 bash -c 'echo "{\"tool_input\":{\"command\":\"git commit -m test\"}}" | .claude/hooks/dbt_pre_commit.sh' 2>/dev/null
assert_exit 0 $? "SKIP_DBT_CHECKS=1 bypass"

# 6. Validator unit tests pass
python3 -m unittest discover -s .claude/skills/enforce-naming-standards/tests -v
assert_exit 0 $? "validator unit tests"

echo "all smoke checks passed"
