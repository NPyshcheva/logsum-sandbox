# Provenance — logsum replay (2026-07-05)

## Model
claude-sonnet-4-6

## Context loaded
- `spec.md` — authoritative source; read in full before writing any artefact
- `CLAUDE.md` — conventions and escalation gates
- Prior conversation summary — used for continuity only; no artefacts carried forward from it

## Files changed

| File | Action |
|---|---|
| `src/logsum.py` | Rewritten from spec; `_normalise_row` refactor applied in step 5 |
| `tests/test_logsum.py` | Rewritten; 81 tests across 9 classes |
| `tests/fixtures/simple.csv` | Rewritten |
| `tests/fixtures/whitespace_fields.csv` | Rewritten |
| `tests/fixtures/missing_level.csv` | Rewritten |
| `tests/fixtures/malformed_ts.csv` | Rewritten |
| `tests/fixtures/all_malformed_ts.csv` | Rewritten |
| `tests/fixtures/header_only.csv` | Rewritten |
| `tests/fixtures/no_header.csv` | Rewritten |
| `.github/workflows/ci.yml` | Already correct; no change needed |
| `provenance.md` | Replaced (this file) |

Files not touched: `spec.md`, `CLAUDE.md`, `test-notes.md`, `questions.md`, `refactor-notes.md`.

## Plan deviations

| Step | Plan said | What happened |
|---|---|---|
| 4 — ci.yml | "Re-write `.github/workflows/ci.yml`" | File was already correct; no edit made |
| 6 — pytest | "Must be 81/81 green" | 81/81 passed on first run |
| Order | Steps executed 1–7 in sequence | Context break between steps 2 and 3; resumed without re-doing completed steps |

No functional deviations from the plan.

## PR provenance block

| Link | Path |
|---|---|
| Spec | `spec.md` |
| Session log | `sessions/cli-events-aggregator/session-log.md`, `sessions/cli-events-aggregator-2/session-log.md` |
| Tests | `tests/test_logsum.py` (81 tests; isolation tier: **limited** — see T-1 in review) |
| Review | `reviews/pr-1/review.md` |

> **T-1 gate cleared** (Nina Pyshcheva, 2026-07-05): limited isolation tier accepted; tests will not be re-generated.  
> **C-1 accepted** (Nina Pyshcheva, 2026-07-05): `message` enforced in input header; current behaviour intentional.  
> **Feature flag gate cleared** (2026-07-05): greenfield implementation, no pre-existing behavior changed; spec-defined CLI flags are the behavior-control mechanism; no feature flag required.

---

## Untested items

- `--min-count 0` — argparse accepts it; behaviour (passes everything) not in spec
- `--min-count` with a negative integer — argparse accepts it; spec does not define the result
- `--min-count` combined with UNKNOWN groups (missing-level rows)
- `--min-count` combined with all-malformed-timestamp groups
- Row-number reporting when `reader.fieldnames` contains duplicates
- Input file encoded other than UTF-8
