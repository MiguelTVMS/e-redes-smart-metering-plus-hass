# Pre-commit Hook

This repository includes a pre-commit hook that automatically validates your code before each commit, ensuring it meets the same quality standards as the GitHub Actions CI/CD pipeline.

## Installation

Run the installation script from the repository root:

```bash
./scripts/install-hooks.sh
```

This will copy the pre-commit hook to `.git/hooks/pre-commit` and make it executable.

## What It Does

The pre-commit hook runs the following checks on staged Python files:

1. **Black** - Code formatting check
2. **isort** - Import ordering check
3. **Ruff** - Linting check
4. **Pytest** - Unit tests (when Python files are staged)

These are the **same checks** that run in GitHub Actions, so you'll catch issues before pushing.

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
  black custom_components/
  isort custom_components/
  ruff check --fix custom_components/
```

## Fixing Issues

If the pre-commit hook blocks your commit, run the suggested fix commands:

```bash
# Auto-fix formatting
black custom_components/

# Auto-fix imports
isort custom_components/

# Auto-fix linting issues
ruff check --fix custom_components/

# Run tests to see what's failing
pytest tests/ -v
```

Then stage the fixed files and commit again:

```bash
git add custom_components/
git commit -m "Your commit message"
```

## Bypassing the Hook

**Not recommended**, but you can skip the hook in emergencies:

```bash
git commit --no-verify -m "Your commit message"
```

⚠️ **Warning:** Bypassing the hook may cause your PR to fail GitHub Actions checks.

## Troubleshooting

### "Linting tools not found"

The hook will automatically install dependencies if needed. However, you can manually install them:

```bash
pip install -r requirements_dev.txt
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
python --version  # Should be Python 3.13
pip install -r requirements_dev.txt
```

## Benefits

- ✅ **Catch issues early** - Before pushing to GitHub
- ✅ **Consistent code quality** - Automatic formatting and linting
- ✅ **Faster feedback** - No need to wait for CI/CD
- ✅ **Less review friction** - Code already meets standards
- ✅ **Same as CI** - Uses identical checks as GitHub Actions

## Uninstalling

To remove the pre-commit hook:

```bash
rm .git/hooks/pre-commit
```

---

**Note:** The `.git/hooks` directory is not tracked by Git, so each contributor needs to install the hook separately using `./scripts/install-hooks.sh`.
