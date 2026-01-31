#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$ROOT_DIR/scripts/get_bump_type.sh"

if [[ ! -x "$SCRIPT" ]]; then
  echo "get_bump_type.sh is not executable" >&2
  exit 1
fi

run_case() {
  local name="$1"
  local expected="$2"
  local tmp
  tmp=$(mktemp -d)
  git -C "$tmp" init -q
  git -C "$tmp" config user.email "test@example.com"
  git -C "$tmp" config user.name "Test"

  echo "base" > "$tmp/file.txt"
  git -C "$tmp" add file.txt
  git -C "$tmp" commit -q -m "chore: base"
  git -C "$tmp" tag v0.1.0

  shift 2
  for msg in "$@"; do
    echo "$msg" >> "$tmp/file.txt"
    git -C "$tmp" add file.txt
    git -C "$tmp" commit -q -m "$msg"
  done

  echo "--- $name ---" >&2
  local result
  result=$(cd "$tmp" && "$SCRIPT")
  if [[ "$result" != "$expected" ]]; then
    echo "FAIL: $name expected=$expected got=$result" >&2
    exit 1
  fi
  echo "PASS: $name" >&2
}

run_case "Only feat commits" "minor" \
  "feat: add feature"

run_case "Fix and feat commits" "minor" \
  "fix: bugfix" \
  "feat: add feature"

run_case "BREAKING CHANGE present" "major" \
  "feat!: breaking api" \
  "fix: followup"

run_case "Only chore commits" "none" \
  "chore: tidy" \
  "docs: update readme" \
  "ci: update workflow"

# Scenario: no tags in repo
(
  tmp=$(mktemp -d)
  git -C "$tmp" init -q
  git -C "$tmp" config user.email "test@example.com"
  git -C "$tmp" config user.name "Test"
  echo "init" > "$tmp/file.txt"
  git -C "$tmp" add file.txt
  git -C "$tmp" commit -q -m "feat: first feature"
  echo "--- No tag repo ---" >&2
  result=$(cd "$tmp" && "$SCRIPT")
  if [[ "$result" != "minor" ]]; then
    echo "FAIL: no tag repo expected=minor got=$result" >&2
    exit 1
  fi
  echo "PASS: no tag repo" >&2
)

echo "All tests passed." >&2
