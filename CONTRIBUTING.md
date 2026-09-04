# Contributing

Contributions are welcome! Please follow these guidelines:

## Development Setup

See the [cross-platform development guide](docs/DEVELOPMENT.md) for verified Windows, macOS, and Linux prerequisites, bootstrap behavior, Docker usage, and troubleshooting.

1. Fork the repository
2. Clone your fork
3. **Important:** This repository uses the gitflow branching model. All new development should be done on the `develop` branch, never on `main`. Please base your feature branches and pull requests on `develop`.
4. Install [uv](https://docs.astral.sh/uv/) and Docker Desktop.
5. Bootstrap the local Python 3.14 environment:

   ```bash
   make bootstrap
   ```

6. Start the development Home Assistant instance:

   ```bash
   make ha-up
   ```

7. Open `http://localhost:8123`. The development stack completes onboarding automatically. Use `make ha-credentials` only if the trusted-network login is unavailable.

The integration source is mounted directly into Home Assistant. Restart Home Assistant after changing Python code:

```bash
make ha-restart
```

The Home Assistant configuration is stored in the ignored `config/` directory and persists between container restarts.

### Local development commands

Command | Purpose
-- | --
`make bootstrap` | Install Python 3.14, dependencies, and the Git hook
`make doctor` | Verify the Python, Docker, and Compose development environment
`make validate` | Format, lint, and run the complete test suite
`make test` | Run the test suite only
`make ha-up` | Start Home Assistant in the background
`make ha-down` | Stop Home Assistant
`make ha-restart` | Restart Home Assistant after integration changes
`make ha-logs` | Follow Home Assistant logs
`make webhook` | Send a representative payload to the local webhook
`make simulate` | Continuously send changing meter data to the local webhook

The same commands are available from **Terminal > Run Task** in VS Code.

The pre-commit hook automatically runs the primary Python 3.14 and Home Assistant 2026.9 checks before each commit. GitHub Actions also runs the full test suite on the minimum supported Python 3.13 and Home Assistant 2026.1 environment.

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
- ✅ Mypy type checking
- ✅ Pytest tests

If any check fails, the commit will be blocked until you fix the issues.

### Manual Checks

Run the same formatting and validation sequence used by the repository instructions:

```bash
make validate
```

**Note:** These are the primary-environment checks that run in GitHub Actions. CI also runs the test suite against the minimum supported Home Assistant version. Installing the pre-commit hook ensures you catch current-version issues early, before pushing to GitHub.

## Pull Request Process

1. Ensure all tests pass
2. Target branch: open pull requests against `develop` (not `main`)
3. Update documentation if needed
4. Follow the existing code style
5. Write clear commit messages
6. Submit a pull request with a clear description

## Reporting Issues

Please use the GitHub issue tracker to report bugs or request features.
Include the following diagnostic information when it is relevant:

- Home Assistant version
- Integration version
- Steps to reproduce
- Error logs (if applicable)

Remove CPEs, webhook URLs, authentication tokens, credentials, and unredacted payload data before posting. A payload can disclose household energy usage even when it contains no account credentials.

Thank you for contributing!
