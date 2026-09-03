# E-REDES Smart Metering Plus agent guide

## Purpose

This repository contains a Home Assistant custom integration for E-REDES Smart Metering Plus meters in Portugal. It receives webhook payloads and creates a separate Home Assistant device for each allowed CPE.

Keep instructions here operational. Product setup belongs in `README.md`; contributor setup belongs in `docs/DEVELOPMENT.md` and `CONTRIBUTING.md`.

## Working contract

- For questions, reviews, diagnosis, or plans, inspect the relevant files and report evidence. Do not implement a change unless requested.
- For a requested change, make the smallest in-scope local change and run the relevant non-destructive validation without asking first.
- Ask before external writes, destructive actions, new production dependencies, purchases, or a material expansion of scope.
- Preserve user changes. Inspect `git status --short` before editing and do not discard, reformat, or include unrelated files.
- Use `rg` for repository searches. Read the focused source and tests before changing behavior.
- On Windows, use `winget` for any required tool installation. Do not install a tool that is already available.
- Lead responses with the outcome. State assumptions, failures, and any required user action plainly.

## Repository facts

- Target Home Assistant version: `2026.1.0`.
- Python tooling: Python 3.13 managed by `uv` in `.venv`.
- Home Assistant and Windows test execution use Docker Compose. Do not try to make native Windows pytest a supported path.
- `config/` is ignored local Home Assistant state. It can contain credentials, tokens, CPEs, and recorder data. Never commit, copy, or expose its contents.
- `make` is the cross-platform command surface. Use `make doctor`, `make bootstrap`, `make validate`, `make test`, and the `make ha-*` commands described in `docs/DEVELOPMENT.md`.
- Feature branches and pull requests target `develop`. Do not push, create a pull request, or change GitHub repository settings unless the user explicitly asks.

## Integration invariants

- The integration is UI-configured. Do not require user YAML or automations for normal operation.
- `WEBHOOK_ID` is `DOMAIN`; the endpoint path is fixed at `/api/webhook/e_redes_smart_metering_plus`.
- A CPE must match `PT` followed by 18 uppercase alphanumeric characters. Treat configured CPEs as an allowlist and reject all other payloads.
- One accepted CPE creates and updates only its own device and entities. Preserve multi-meter isolation.
- Prefer a configured Home Assistant external URL. Otherwise use a Home Assistant Cloud Cloudhook when available; otherwise expose the local generated webhook URL.
- Preserve incoming measurement timestamps and reject older out-of-order data for a CPE.
- Estimated power usage is based on active power, voltage, and the selected contracted-power tier. Preserve its explicit power-factor limitation and never present it as a physical breaker prediction. Diagnostic alert entities are disabled by default.
- Keep entity names, translations, icons, device classes, state classes, units, and entity categories consistent when adding or changing entities.

## Change workflow

1. Locate the real code path and the nearest relevant tests.
2. Change production code, tests, translations, documentation, and metadata together when behavior or user-visible text changes.
3. Run `make validate` after any Python, translation, manifest, or integration behavior change. It formats, lints, and runs the full test suite.
4. For documentation-only changes, run `git diff --check`; validate edited JSON with PowerShell `ConvertFrom-Json` when applicable.
5. Report commands run and their result. Do not claim browser or Home Assistant behavior without observing it.

## Data handling and review rules

- Never place webhook URLs, CPEs, access tokens, credentials, `.storage` data, or unredacted payloads in commits, issues, screenshots, or public documentation.
- For a review, report only actionable correctness, security, regression, data-isolation, or test-coverage findings. Include file references and evidence. Leave formatting to the automated checks.
- Keep examples minimal and use placeholders for identifiers and URLs.
