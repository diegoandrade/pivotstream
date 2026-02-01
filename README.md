# PivotStream Studio

[![Code of Conduct](https://img.shields.io/badge/Code%20of%20Conduct-Contributor%20Covenant%202.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

A lightweight RSVP (rapid serial visual presentation) reader that keeps the Optimal Recognition Point (ORP) fixed in the center so your eyes don’t move. Paste text or import an EPUB/PDF, set WPM, and read.

## Features
- RSVP display with fixed ORP alignment
- Adjustable speed (100–1600 WPM)
- Play / pause / resume / restart
- Jump forward/back by 10 words
- Text paste + EPUB/PDF import

## Requirements
- Python 3.11+

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
uvicorn main:app --reload --reload-exclude .venv
```
Then open `http://127.0.0.1:8000`.

## Usage
- Paste text into the textarea and click **Play**.
- Use **Load sample text** for a quick demo.
- Use **Choose EPUB** + **Load EPUB** to import a book.
- Use **Choose PDF** + **Load PDF** to import a document.
- Adjust WPM anytime.

## Development
### Pre-commit
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Code of Conduct
We are committed to fostering a welcoming community. Please review the Code of Conduct before contributing: `CODE_OF_CONDUCT.md`.

### Changelog
Generate or update `CHANGELOG.md` locally:
```bash
git cliff -o CHANGELOG.md
```

## Notes
- If you see reload loops, ensure `.venv` is excluded from the watcher.
