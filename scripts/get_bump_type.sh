#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '%s\n' "$*" >&2
}

if ! command -v git >/dev/null 2>&1; then
  log "Error: git is required."
  echo "none"
  exit 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  log "Error: not a git repository."
  echo "none"
  exit 1
fi

LAST_TAG=""
if LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null); then
  :
else
  LAST_TAG=""
fi

RANGE=""
if [[ -n "$LAST_TAG" ]]; then
  RANGE="${LAST_TAG}..HEAD"
  log "Using range: ${RANGE}"
else
  RANGE="HEAD"
  log "No tags found. Using full history."
fi

COMMITS=$(git log --format='%H%n%s%n%b%n==END==' "$RANGE" || true)
if [[ -z "$COMMITS" ]]; then
  log "No commits found in range."
  echo "none"
  exit 0
fi

bump="none"

commit_id=""
subject=""
body=""
state=0

is_breaking_subject() {
  local subj="$1"
  echo "$subj" | grep -Eq '^[a-zA-Z]+(\([^)]+\))?!:' && return 0
  return 1
}

is_breaking_body() {
  local text="$1"
  echo "$text" | grep -Eq "(^|[[:space:]])BREAKING CHANGE:|(^|[[:space:]])BREAKING-CHANGE:" && return 0
  return 1
}

process_commit() {
  local cid="$1"
  local subj="$2"
  local bod="$3"

  if is_breaking_subject "$subj" || is_breaking_body "$bod"; then
    log "MAJOR: $cid $subj"
    bump="major"
    return
  fi

  if echo "$subj" | grep -Eq '^feat(\(|:)' ; then
    if [[ "$bump" != "major" ]]; then
      log "MINOR: $cid $subj"
      bump="minor"
    fi
    return
  fi

  if echo "$subj" | grep -Eq '^fix(\(|:)' ; then
    if [[ "$bump" != "major" && "$bump" != "minor" ]]; then
      log "PATCH: $cid $subj"
      bump="patch"
    fi
    return
  fi

  if echo "$subj" | grep -Eq '^(chore|docs?|ci|test)(\(|:)' ; then
    log "NONE: $cid $subj"
    return
  fi

  log "NONE: $cid $subj"
}

while IFS= read -r line; do
  if [[ "$line" == "==END==" ]]; then
    if [[ -n "$commit_id" ]]; then
      process_commit "$commit_id" "$subject" "$body"
    fi
    commit_id=""
    subject=""
    body=""
    state=0
    continue
  fi

  if [[ $state -eq 0 ]]; then
    commit_id="$line"
    state=1
    continue
  fi
  if [[ $state -eq 1 ]]; then
    subject="$line"
    state=2
    continue
  fi
  if [[ $state -ge 2 ]]; then
    if [[ -z "$body" ]]; then
      body="$line"
    else
      body="$body
$line"
    fi
  fi

done <<< "$COMMITS"

if [[ "$bump" == "major" ]]; then
  echo "major"
  exit 0
fi
if [[ "$bump" == "minor" ]]; then
  echo "minor"
  exit 0
fi
if [[ "$bump" == "patch" ]]; then
  echo "patch"
  exit 0
fi

echo "none"
