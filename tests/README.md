# Test suite

The test suite covers config entry setup and migration, webhook validation and authentication, Cloudhook lifecycle, multi-meter isolation, dynamic entity discovery, contracted-power calculations, device deletion and full reset, translations and icons, local tooling, and the development environment pins.

## Supported environments

| Environment | Purpose | Where it runs |
| --- | --- | --- |
| Python 3.14 and Home Assistant 2026.9 | Primary development and current-release compatibility | Local `.venv`, Linux and macOS CI, and the Docker test image |
| Python 3.13 and Home Assistant 2026.1 | Declared minimum-version compatibility | Dedicated Linux CI job |
| PowerShell and Docker Desktop | Windows command and script validation | Windows CI; pytest runs in the Linux Docker test image |

## Commands

Run the complete repository validation from the project root:

```console
make validate
```

Run only the tests:

```console
make test
```

Run a focused test from the primary environment on macOS or Linux:

```console
.venv/bin/python -m pytest tests/test_webhook.py -q
```

Use `requirements_dev_minimum.txt` in a separate Python 3.13 virtual environment to reproduce minimum-version CI. Do not replace the primary `.venv` dependencies with the minimum constraints.

## Test isolation

The suite uses `pytest-homeassistant-custom-component` and Home Assistant core fixtures. Home Assistant Cloud is mocked, webhook requests remain local, and tests must not read the ignored `config/` directory. Use placeholder CPEs and tokens in fixtures. Never add real CPEs, webhook URLs, credentials, recorder data, or production payloads.

Every behavior change should include the nearest focused regression test. Changes to metadata, development baselines, scripts, translations, or icons must update their corresponding validation tests as well.
