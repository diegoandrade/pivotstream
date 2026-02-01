# Contributing

By participating in this project, you agree to abide by our Code of Conduct.

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

## Conventional Commits
All commits and PR titles must follow the Conventional Commits format:
```
type(scope): description
```

Types: `feat`, `fix`, `docs`, `chore`, `ci`, `test`, `refactor`, `perf`, `security`
Scopes: `cli`, `core`, `subprocess`, `docs`, `ci`, `deps`

Guidelines:
- Use the imperative mood in the subject (e.g., "add", "fix", "update").
- Keep the subject lowercase and at least 10 characters.
- Use `!` or a `BREAKING CHANGE:` footer for breaking changes.

### Valid PR titles
- `fix(core): resolve timeout handling in monitor thread`
- `docs: update installation instructions`
- `chore(deps): bump ruff to v0.15.0`
- `feat(cli)!: change default config file location (BREAKING)`

### Invalid PR titles
- `Add new feature` (missing type)
- `feat: adds support` (wrong verb tense; use imperative)
- `FIX: bug` (wrong case)
- `feature(core): new API` (wrong type)

### Commit message template
We provide a commit template at `.gitmessage`. Configure it locally:
```bash
git config commit.template .gitmessage
```

### Local validation hooks
Enable the local commit-msg hook and pre-commit validation:
```bash
git config core.hooksPath .githooks
pre-commit install --hook-type commit-msg
```

### Bump examples
- **major**: `feat(core)!: remove deprecated config` or footer `BREAKING CHANGE: remove legacy API`
- **minor**: `feat(cli): add interactive setup`
- **patch**: `fix(core): handle empty input`

### Migration guide (why + how)
We use conventional commits to automate releases, changelogs, and version bumps.

If you need to rewrite recent commits:
```bash
git rebase -i HEAD~3
# change "pick" to "reword" for commits you need to edit
```

Cheat sheet:
- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation changes
- `chore`: maintenance tasks
- `ci`: CI workflow changes
- `test`: tests only
- `refactor`: code refactor (no behavior change)
- `perf`: performance improvements
- `security`: security fixes

## Commit Message Guidelines
### Overview
We use conventional commits to automate changelog generation and semantic versioning. This keeps releases consistent and predictable.

### Format Specification
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Type Reference Table
| Type | Description | Version Bump | Examples |
|------|-------------|--------------|----------|
| feat | New feature | MINOR | feat(subprocess): add pdf wrapper |
| fix | Bug fix | PATCH | fix(core): handle missing config file |
| docs | Documentation only | NONE | docs: update API reference |
| chore | Maintenance | NONE | chore(deps): update pytest to 8.0 |
| ci | CI/CD changes | NONE | ci: add macOS to test matrix |
| test | Add/update tests | NONE | test(subprocess): add api timeout tests |
| refactor | Code restructure | NONE | refactor(core): simplify error handling |
| perf | Performance improvement | PATCH | perf(core): optimize subprocess monitoring |
| security | Security fix | PATCH | security: sanitize user input |

### Breaking Changes
- Indicate with `!` after type/scope: `feat(core)!: remove legacy config loader`
- Or add a footer: `BREAKING CHANGE: remove support for .ini configs`
- Use for changes that require users to modify code or configuration; these map to a MAJOR version bump.

### Scope Guidelines
Available scopes:
- `cli`: command-line interface and flags
- `core`: core reader logic, timing, parsing, rendering
- `subprocess`: external process integration and wrappers
- `docs`: documentation content and structure
- `ci`: CI/CD workflows and tooling
- `deps`: dependency updates

Use a scope when the change is localized; omit it for repo-wide changes.

Examples:
- `feat(cli): add --theme flag`
- `fix(core): prevent zero-length tokens`
- `docs: update quickstart`

### Best Practices
- Use imperative mood ("add", not "added" or "adds")
- Keep description under 72 characters
- Reference issues in the footer: `Fixes #123`
- Use the body to explain **why**, not **what**

### Real Examples (PivotStream)
- Updating documentation:
  - `docs: clarify EPUB import steps`
  - `docs: add troubleshooting for PDF parsing`

### Troubleshooting (pre-commit hooks)
- **Hook not running**: run `pre-commit install --hook-type commit-msg` and set `git config core.hooksPath .githooks`.
- **Invalid scope/type**: verify the type and scope are in the allowed lists above.
- **Short description error**: keep the subject at least 10 characters.

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

## First-Time Release Setup
- [ ] Install git-cliff locally: `pip install -e ".[release]"`
- [ ] Configure bot access (see `docs/internal/bot-setup.md`) and add `RELEASE_BOT_TOKEN` as a GitHub secret (SECRET)
- [ ] Run the Release Automation workflow on a feature branch to verify it opens a PR
- [ ] Set up branch protection rules for `main` (require PR reviews, prevent direct pushes)

## Troubleshooting
- **Bot token authentication failures**: verify `RELEASE_BOT_TOKEN` exists in repo secrets and the bot has Contents/PR write access.
- **Changelog generation errors**: ensure `git-cliff` installs successfully and `cliff.toml` is valid.
- **PR creation conflicts**: check for an existing open PR from `bot/release/vX.Y.Z`, or delete the stale branch.
- **Tag already exists**: delete the tag if it was created accidentally, or bump the version and rerun.
