# logsum-sandbox

## Project context
Tiny CLI that reads `events.csv` (timestamp, level, service, message) and writes
`summary.csv` with one aggregated row per `(service, level)` group.
Behaviour is fully specified in `../spec.md` (signed off 2026-07-05).

## Layout
- `src/`   — production source
- `tests/` — pytest test suite
- `data/`  — synthetic CSV fixtures only (no real log data)

## Conventions
- Python 3.11; use the standard library — no third-party runtime deps.
- Lint/format with **ruff**; test with **pytest**.
- Follow the normalisation and exit-code rules in spec.md exactly.

## Escalation gates — stop and ask before:
- Adding any dependency outside the Python 3.11 stdlib.
- Using or generating non-synthetic data in `data/`.
- Modifying or overwriting `spec.md` after sign-off.
