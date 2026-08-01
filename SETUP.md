# Setup Guide for ChEMBLdb-query

This document explains how to set up the ChEMBLdb-query project for members of the `data` group.

## Project Location

The project lives on the NVMe-backed volume at `/opt/ljubomir/ChEMBLdb-query`.

**Create a symlink from your home directory:**

```bash
ln -s /opt/ljubomir/ChEMBLdb-query ~/ChEMBLdb-query
cd ~/ChEMBLdb-query
```

## Prerequisites

You need:
- Python 3.13 (available system-wide at `/usr/bin/python3.13`)
- `uv` package manager (if not installed, see below)
- Membership in the `data` group

### Installing uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Prefer the installer script above for this repo workflow.

## Setup Steps

### 1. Navigate to the project

```bash
cd ~/ChEMBLdb-query
```

### 2. Create the virtual environment

**Important:** Use the system Python, not your user-local Python, so the environment is portable.

```bash
uv venv --python /usr/bin/python3.13
```

### 3. Install dependencies

```bash
uv sync
```

This installs:
- Core dependencies (anthropic, dspy, polars, requests)
- Dev dependencies (pytest, zstandard)

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 5. Set umask for collaboration (recommended)

For files to be editable by all `data` group members, set a permissive umask:

```bash
# Temporarily (current session only)
umask 007
```

To make this persistent for this project, add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Set group-writable permissions for ChEMBLdb-query project
alias cdchembl='cd ~/ChEMBLdb-query && umask 007'
```

Then use `cdchembl` to enter the project with collaborative permissions.

**Note:** The project directory already has the setgid bit set, so new files automatically inherit the `data` group ownership. The umask ensures they're group-writable.

## Running the Project

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Run tests:

```bash
pytest
```

Use the query tool:

```bash
python src/db_llm_query.py --help
```

## Troubleshooting

### "Permission denied" errors

Ensure you're in the `data` group:
```bash
groups
```

If not, ask your admin to add you:
```bash
sudo usermod -a -G data YOUR_USERNAME
```

### Python version mismatch

The project requires Python 3.13. Check you have it:
```bash
/usr/bin/python3.13 --version
```

### Virtual environment issues

If you encounter problems, delete and recreate:
```bash
rm -rf .venv
uv venv --python /usr/bin/python3.13
uv sync
```

## Project Structure

- `src/` - Source code
- `tests/` - Test suite
- `database/` - ChEMBL database connection details
- `scripts/` - Utility scripts
- `pyproject.toml` - Project configuration and dependencies
- `.python-version` - Required Python version (3.13)

## Getting Help

- See `README.md` for project documentation
- See `AGENTS.md` for agent-related documentation
- Check `LEARNINGS.md` for project-specific insights and gotchas
