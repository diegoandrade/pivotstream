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
