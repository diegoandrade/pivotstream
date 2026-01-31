#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <version-tag> (e.g., v1.2.0)" >&2
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

TAG="$1"

if ! command -v git-cliff >/dev/null 2>&1; then
  echo "Error: git-cliff is not installed. Install with: pip install -e .[release]" >&2
  exit 1
fi

if ! git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null; then
  echo "Error: tag '${TAG}' does not exist." >&2
  exit 1
fi

PREV_TAG=""
if git describe --tags --abbrev=0 "${TAG}^" >/dev/null 2>&1; then
  PREV_TAG=$(git describe --tags --abbrev=0 "${TAG}^")
fi

if [[ -n "${PREV_TAG}" ]]; then
  RANGE="${PREV_TAG}..HEAD"
  echo "Generating changelog for ${RANGE} (tag: ${TAG})..."
  git-cliff "${RANGE}" --tag "${TAG}" -o CHANGELOG.md
else
  echo "Generating changelog from repository start to HEAD (tag: ${TAG})..."
  git-cliff --tag "${TAG}" -o CHANGELOG.md
fi

echo "Wrote CHANGELOG.md"
