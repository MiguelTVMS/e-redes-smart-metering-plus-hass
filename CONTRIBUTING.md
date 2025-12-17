# Contributing

Contributions are welcome! Please follow these guidelines:

## Development Setup

1. Fork the repository
2. Clone your fork
3. **Important:** This repository uses the gitflow branching model. All new development should be done on the `develop` branch, never on `main`. Please base your feature branches and pull requests on `develop`.
4. Open the project in VS Code. If prompted, reopen in the devcontainer for a pre-configured development environment.
5. The devcontainer includes Python 3.13 and all required tools. Development dependencies are installed automatically, but you can also run:

   ```bash
   pip install -r requirements_dev.txt
   ```

6. **Install the pre-commit hook** (highly recommended):

   ```bash
   ./scripts/install-hooks.sh
   ```

   This will automatically run linting and tests before each commit, ensuring your code meets quality standards before pushing.

If you are not using VS Code or devcontainers, follow the manual steps above to install dependencies.

### Branching model (gitflow)

- Base all work on the `develop` branch.
- Create branches from `develop` using prefixes like `feature/<name>` or `fix/<name>`.
- Open pull requests into `develop`.
- Maintainers will manage `release/*` and `hotfix/*` branches and merge to `main` when publishing.

## Code Quality

### Pre-commit Hook (Recommended)

The easiest way to ensure code quality is to install the pre-commit hook:

```bash
./scripts/install-hooks.sh
```

This hook automatically runs before each commit and validates:
- ✅ Black formatting
- ✅ isort import ordering
- ✅ Ruff linting
- ✅ Pytest tests

If any check fails, the commit will be blocked until you fix the issues.

### Manual Checks

Alternatively, you can run these checks manually before submitting a pull request:

```bash
# Format imports then code
isort custom_components/
black custom_components/

# Lint code
ruff check custom_components/

# Auto-fix lint issues (optional)
ruff check --fix custom_components/

# Optional static type check
mypy custom_components/ --ignore-missing-imports

# Run tests
pytest tests/
```

**Note:** These are the same checks that run in GitHub Actions. Installing the pre-commit hook ensures you catch issues early, before pushing to GitHub.

## Pull Request Process

1. Ensure all tests pass
2. Target branch: open pull requests against `develop` (not `main`)
2. Update documentation if needed
3. Follow the existing code style
4. Write clear commit messages
5. Submit a pull request with a clear description

## Reporting Issues

Please use the GitHub issue tracker to report bugs or request features.
Include as much detail as possible:

- Home Assistant version
- Integration version
- Steps to reproduce
- Error logs (if applicable)

Thank you for contributing!
