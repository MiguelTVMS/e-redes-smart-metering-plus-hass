# Development environment

The repository provides the same development commands on Windows, macOS, and Linux. Python 3.13 and all Python packages are isolated in `.venv`; Home Assistant 2026.1.0 runs in Docker Compose.

## Prerequisites

All platforms need Git, `uv`, GNU Make, Docker with the Compose plugin, and a running Docker engine.

### Windows

Install missing host tools with Windows Package Manager:

```powershell
winget install --exact --id astral-sh.uv
winget install --exact --id ezwinports.make
winget install --exact --id Docker.DockerDesktop
```

Open a new terminal after installation so the command aliases are available, start Docker Desktop, and use Linux containers.

### macOS

Install `uv` with Homebrew:

```bash
brew install uv
```

Install and start Docker Desktop. macOS normally provides GNU Make through the Xcode Command Line Tools. Verify it with `make --version`. Homebrew also provides GNU Make as `gmake` through `brew install make` if the system command is unavailable.

### Linux

Install GNU Make, Docker Engine, and the Docker Compose plugin with the distribution package manager or Docker's official repository. Install `uv` with its official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ensure the current user can access the Docker engine before continuing.

## Bootstrap

From the repository root, run:

```console
make bootstrap
```

The command:

1. Verifies that Docker is installed and running.
2. Installs or locates Python 3.13 through `uv`.
3. Creates a platform-native `.venv` when needed.
4. Installs `requirements_dev.txt` into that environment.
5. Installs the repository pre-commit hook in the Git-resolved hooks directory.

The Windows implementation uses PowerShell. The macOS and Linux implementation uses Bash. `make` selects the correct script automatically.

Home Assistant imports the POSIX-only `fcntl` module during test startup. On Windows, `make test` and the test phase of `make validate` run the same pytest command in the Linux development container defined by `Dockerfile.tests`. Native Windows pytest is not a supported path.

Verify the complete host setup with:

```console
make doctor
```

## Daily commands

Command | Purpose
-- | --
`make bootstrap` | Create or refresh the Python 3.13 environment and Git hook
`make doctor` | Verify `uv`, Python, Docker Compose, Docker Engine, and Compose configuration
`make validate` | Format source code, lint it, and run the complete test suite
`make test` | Run the complete test suite without formatting
`make ha-up` | Start the Home Assistant development container
`make ha-down` | Stop and remove the development container
`make ha-restart` | Restart Home Assistant after integration code changes
`make ha-logs` | Follow Home Assistant logs
`make ha-onboard` | Rerun the idempotent development onboarding helper
`make ha-credentials` | Show the generated local development login
`make webhook` | Send a representative payload to the local webhook
`make simulate` | Continuously send changing simulated meter data

These commands are also available under **Terminal > Run Task** in VS Code.

## Home Assistant container

The Compose project stores Home Assistant state in the ignored `config/` directory. The integration source directory is mounted read-only at `/config/custom_components/e_redes_smart_metering_plus`, so no copy or `rsync` step is required.

On the first start, Compose copies the tracked files from `dev/home-assistant/` into `config/`. Existing files are never overwritten. The development `configuration.yaml` preconfigures:

- The development instance name and local URL
- Generic central-Portugal coordinates, metric units, EUR, English, and the Europe/Lisbon time zone
- Home Assistant's default UI, config flow, cloud, webhook, and discovery integrations
- Two days of recorder retention
- Info-level logs for this custom integration without enabling payload-level debug logs
- UI-managed automation, script, scene, and theme files

The one-shot `homeassistant-onboarding` service waits for Home Assistant, creates a development owner, and completes the core configuration, analytics, and integration onboarding steps. It generates a strong random fallback password and writes it to the ignored `config/.dev-onboarding.json` file with restrictive permissions. Run `make ha-credentials` only when you need the recovery login. You can set `HOME_ASSISTANT_DEV_NAME`, `HOME_ASSISTANT_DEV_USERNAME`, `HOME_ASSISTANT_DEV_PASSWORD`, or `HOME_ASSISTANT_DEV_LANGUAGE` before the first `make ha-up` to override the generated account.

Local browser access is passwordless through Home Assistant's trusted-network provider. Trust is limited to loopback, the fixed Compose gateway at `172.31.252.1`, and Docker Desktop's internal host gateway at `192.168.65.1`. The normal Home Assistant password provider remains enabled to prevent lockout, and port 8123 remains bound only to the host loopback interface.

The helper is idempotent and does not store access or refresh tokens. It uses Home Assistant 2026.1.0's internal onboarding API, so keep the Compose image pinned and validate the helper when changing that version. The E-Redes integration still uses Home Assistant's UI config-entry storage, so add it after Home Assistant opens and enter the real CPE values you intend to test. Do not copy or commit files from `config/.storage/`; they contain internal state and authentication data.

Start Home Assistant and open `http://localhost:8123`:

```console
make ha-up
```

Onboarding completes automatically. Use `make ha-credentials` to retrieve the generated login, then add the E-Redes integration from **Settings > Devices & services**. Restart the container after changing Python or integration metadata:

```console
make ha-restart
```

The test webhook defaults to `http://localhost:8123/api/webhook/e_redes_smart_metering_plus`. Override its destination or CPE with `WEBHOOK_URL` and `TEST_CPE` environment variables.

### Simulate meter data

First add the simulator's CPE to the integration through **Settings > Devices & services > E-Redes Smart Metering Plus > Configure**. Then start a continuous single-phase household simulation:

```console
make simulate SIMULATOR_ARGS="--cpe PT000000000000000000"
```

Press `Ctrl+C` to stop. The simulator advances cumulative energy from each power sample and updates timestamps, voltage, maximum power, import, and export values. It is deterministic, so developers can reproduce the same state sequence.

Available scenarios are:

- `household`: varied import with brief export periods
- `solar`: a daytime-style transition from import to export
- `contracted-power`: active-power samples equivalent to 50%, 82%, 96%, 105%, and 70% of a nominal current at power factor 1, exercising normal, warning, critical, exceeded, and recovery states

For example, send ten three-phase contracted-power samples one second apart:

```console
make simulate SIMULATOR_ARGS="--cpe PT000000000000000000 --scenario contracted-power --phases 3 --nominal-current-amps 20 --interval 1 --count 10"
```

Select the matching contracted-power tier in Home Assistant before using this scenario. A 20 A nominal current corresponds to 4.60 kVA for a single-phase installation or 13.80 kVA for a three-phase installation.

The simulator and integration derive an active-current estimate from active power and voltage. The E-REDES pilot webhook does not expose current, apparent power, or power factor, so the estimate is a lower bound when power factor is below 1 and cannot predict meter or breaker operation.

Use `--dry-run` to inspect one generated payload without sending it, or `--print-payload` to display every payload while sending. Run the complete option reference with:

```console
.venv/bin/python scripts/simulate-webhook.py --help
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`. The same settings are available through the `WEBHOOK_URL`, `TEST_CPE`, `SIMULATION_SCENARIO`, `SIMULATION_INTERVAL`, `SIMULATION_COUNT`, `SIMULATION_PHASES`, and `SIMULATION_NOMINAL_CURRENT_AMPS` environment variables.

## Validation contract

`make validate` runs the repository-required commands in this order:

```console
black custom_components/
isort custom_components/
ruff check --fix custom_components/
black tests/ scripts/
isort tests/ scripts/
ruff check --fix tests/ scripts/
black --check --diff custom_components/
isort --check-only --diff custom_components/
ruff check custom_components/
black --check --diff tests/ scripts/
isort --check-only --diff tests/ scripts/
ruff check tests/ scripts/
mypy custom_components/
pytest tests/ -q --tb=short
```

Run it before every commit. The installed Git hook runs the non-mutating checks when Python files are staged.

On macOS and Linux, pytest runs from `.venv`. On Windows, Docker Compose executes the exact `pytest tests/ -q --tb=short` command inside the test image.

## Platform details

- Windows virtual environments use `.venv\Scripts`; macOS and Linux use `.venv/bin`.
- The Windows virtual environment supplies editor analysis, Black, isort, and Ruff. Home Assistant and pytest run in Linux containers.
- VS Code points at the `.venv` directory so the Python extension resolves the native interpreter on each platform.
- Shell scripts are committed with LF endings to keep Bash and Git hooks executable after a Windows checkout.
- Git hook installation uses `git rev-parse --git-path`, so normal clones and linked worktrees are both supported.
- Docker runs the Linux Home Assistant image on all hosts.

## Troubleshooting

### Docker is unavailable

Start Docker Desktop or the Docker Engine, then confirm `docker info` and `docker compose version` succeed.

### Port 8123 is already in use

Stop the conflicting service or change the host-side port in `docker-compose.yml` before running `make ha-up`.

### Recreate the Python environment

The bootstrap command automatically replaces `.venv` when it is missing or is not using Python 3.13. To refresh installed dependencies without deleting it, run `make bootstrap` again.

### Windows reports a uv installation-link error

The bootstrap checks `uv python find 3.13` after that error. It proceeds only when the requested runtime is actually available.
