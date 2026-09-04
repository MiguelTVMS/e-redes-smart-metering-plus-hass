# Pre-commit Hook

This repository includes a pre-commit hook that validates staged Python changes before each commit. It matches the primary Python 3.14 and Home Assistant 2026.9 checks. GitHub Actions separately tests the Home Assistant 2026.1 minimum.

## Installation

Bootstrap the local development environment from the repository root:

```bash
make bootstrap
```

This installs the Python 3.14 development dependencies and copies the pre-commit hook to Git's resolved hooks directory, including in a linked worktree.

On Windows, the same command delegates to the repository PowerShell bootstrap. See the [cross-platform development guide](DEVELOPMENT.md) for prerequisites and troubleshooting on every supported host.

## What It Does

The pre-commit hook runs the following checks on staged Python files:

1. **Black** - Code formatting check
2. **isort** - Import ordering check
3. **Ruff** - Linting check
4. **Mypy** - Static type checking
5. **Pytest** - Unit tests (when Python files are staged)

These are the same primary-environment checks that run in GitHub Actions, so you'll catch issues before pushing. CI additionally runs the full test suite against the minimum supported Home Assistant version.

## How It Works

When you run `git commit`, the hook will:

1. ✅ Detect if any Python files are staged
2. ✅ Run all validation checks
3. ✅ Allow the commit if all checks pass
4. ❌ Block the commit and show errors if any check fails

## Example Output

### Successful Commit
```
🔍 Running pre-commit validations...

📝 Staged Python files:
custom_components/e_redes_smart_metering_plus/sensor.py

🖤 Running black...
✅ Black check passed

📦 Running isort...
✅ isort check passed

🔧 Running ruff...
✅ Ruff check passed

🔎 Running mypy...
✅ Mypy check passed

🧪 Running pytest...
✅ Tests passed

✅ All pre-commit checks passed!
```

### Failed Commit
```
🔍 Running pre-commit validations...

📝 Staged Python files:
custom_components/e_redes_smart_metering_plus/sensor.py

🖤 Running black...
❌ Black formatting check failed!
💡 Run 'black custom_components/' to fix formatting issues

❌ Pre-commit checks failed! Please fix the issues above before committing.

Quick fix commands:
  black custom_components/ tests/ scripts/
  isort custom_components/ tests/ scripts/
  ruff check --fix custom_components/ tests/ scripts/
```

## Fixing Issues

If the pre-commit hook blocks your commit, run the suggested fix commands:

```bash
make validate
```

Then stage the fixed files and commit again:

```bash
git add custom_components/
git commit -m "Your commit message"
```

## Bypassing the Hook

Do not bypass the hook for ordinary development. If an exceptional recovery requires it, run the complete `make validate` command before pushing and explain the bypass in the pull request.

The Git command is:

```bash
git commit --no-verify -m "Your commit message"
```

Bypassing the hook does not bypass GitHub Actions and does not make an unvalidated commit acceptable for review.

## Troubleshooting

### "Linting tools not found"

Create or refresh the repository-local environment:

```bash
make bootstrap
```

### Hook Not Running

Ensure the hook is executable:

```bash
chmod +x .git/hooks/pre-commit
```

Or reinstall it:

```bash
./scripts/install-hooks.sh
```

### Dependencies Installation Failed

Make sure you're in the correct Python environment:

```bash
.venv/bin/python --version  # Should be Python 3.14
make bootstrap
```

## Benefits

- ✅ **Catch issues early** - Before pushing to GitHub
- ✅ **Consistent code quality** - Automatic formatting and linting
- ✅ **Faster feedback** - No need to wait for CI/CD
- ✅ **Less review friction** - Code already meets standards
- ✅ **Matches primary CI** - Uses the current Home Assistant checks from GitHub Actions

## Uninstalling

To remove the pre-commit hook:

```bash
rm .git/hooks/pre-commit
```

---

**Note:** The `.git/hooks` directory is not tracked by Git, so each contributor needs to install the hook separately. `make bootstrap` is the preferred installation path because it also verifies and prepares the required environment.
