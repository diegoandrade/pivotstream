# Contributing

Thanks for helping improve PivotStream!

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Release tooling (git-cliff)
Install the optional release dependencies:
```bash
pip install -e ".[release]"
```

Generate the changelog:
```bash
git cliff -o CHANGELOG.md
```

## Pre-commit
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Release Process
Releases are fully automated via GitHub Actions.

### Manual initiation
- Run the **Release Automation** workflow (workflow_dispatch).
- The workflow determines the bump type, calculates the next version, generates the changelog, and opens a PR from `bot/release/vX.Y.Z` with label `release`.

### PR updates
- Any push to `bot/release/*` regenerates the changelog and updates the PR automatically.

### Release creation
- When the release PR is merged into `main`, the workflow tags the merge commit, creates the GitHub release, and marks it as the latest.

### Local checks (optional)
```bash
scripts/test_bump_type.sh
```

### Branch protection
Branch protection rules (e.g., required PR reviews) must be configured in GitHub repository settings.
