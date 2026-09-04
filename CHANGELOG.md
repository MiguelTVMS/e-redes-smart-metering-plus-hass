# Changelog

All notable user-facing changes are recorded here. Versions follow semantic versioning and published tags use the `v<version>` format.

## 1.8.2

- Documented the three integration configuration sections and the complete authentication workflow.
- Added a regression test proving that disabling authentication accepts headerless webhooks even when the saved token is retained.
- Clarified the differences between deleting a meter device, fully resetting a meter, and removing a CPE from the allowlist.
- Added webhook response and out-of-order timestamp troubleshooting.
- Documented current and minimum development and test environments across macOS, Linux, Windows, and Docker.
- Corrected contributor onboarding and expanded privacy guidance for support and tests.
- Added documentation link and version consistency checks, including CI coverage for documentation-only pull requests.

## 1.8.1

- Restored startup compatibility with Home Assistant 2026.9 after removal of a legacy entity ID helper.
- Updated entity and device registry handling while retaining Home Assistant 2026.1 compatibility.
- Moved the primary development baseline to Home Assistant 2026.9 and Python 3.14.
- Added explicit Home Assistant 2026.1 and Python 3.13 minimum-version CI coverage.

## 1.8.0

- Split integration configuration into webhook settings, allowed CPE management, and meter reset actions.
- Added optional `Authorization` header validation with random token generation.
- Added meter deletion and full reset workflows that preserve the integration and recreate the meter from its next accepted payload.
