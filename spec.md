# CLI Spec — events aggregator

## Overview

A command-line tool that reads `events.csv`, groups rows by `(service, level)`, and writes one summary row per group to `summary.csv`.

---

## 1. Group key

Each unique `(service, level)` pair — both values taken **after normalisation** (section 2) — defines one output row.

---

## 2. Normalisation rules

| Field       | Rule                                                  | Example                     |
|-------------|-------------------------------------------------------|-----------------------------|
| `level`     | Strip surrounding whitespace, then uppercase          | `"warn "` → `"WARN"`        |
| `service`   | Strip surrounding whitespace, then lowercase          | `" Auth "` → `"auth"`       |
| `timestamp` | Strip surrounding whitespace before parsing           | `" 2024-01-02T10:00:00Z "` → parsed |
| `message`   | Not normalised; not included in the output            | —                           |

Fields are read from the CSV header by name; column order is irrelevant.

---

## 3. Output columns

`summary.csv` has exactly these columns in this order:

```
service, level, count, first_seen, last_seen
```

- `count` — integer; number of input rows in the group.
- `first_seen` — earliest valid timestamp in the group, written in `YYYY-MM-DDTHH:MM:SSZ` format.
- `last_seen` — latest valid timestamp in the group, same format.

If **all** rows in a group carry malformed timestamps, `first_seen` and `last_seen` are written as empty strings (`""`).

---

## 4. Missing `level` behaviour

- A row whose `level` cell is absent or blank is normalised to the sentinel value `"UNKNOWN"`.
- The row is still counted and participates in `first_seen`/`last_seen` calculation.
- One `WARNING` line is written to **stderr** per affected row:
  ```
  WARNING: row <n>: missing level, using "UNKNOWN"
  ```

---

## 5. Malformed timestamp behaviour

- The row still contributes to `count`.
- The row is **excluded** from `first_seen`/`last_seen` computation.
- One `WARNING` line is written to **stderr** per affected row:
  ```
  WARNING: row <n>: cannot parse timestamp "<value>", excluded from time range
  ```
- If all rows in a group are affected, both time fields are written as `""` (see section 3).

---

## 6. Empty input behaviour

| Scenario                             | Behaviour                                      |
|--------------------------------------|------------------------------------------------|
| Input file does not exist            | Exit `2`; write error message to stderr        |
| Input file exists, zero data rows    | Write header-only `summary.csv`; exit `0`      |
| Input file exists, header row absent | Exit `3`; write error message to stderr        |

"Zero data rows" includes a file that contains only a header line or only blank lines.

---

## 7. CLI flags and exit codes

### Flags

| Flag                   | Default        | Description                              |
|------------------------|----------------|------------------------------------------|
| `-i / --input PATH`    | `events.csv`   | Path to the input CSV file               |
| `-o / --output PATH`   | `summary.csv`  | Path to the output CSV file              |
| `--min-count N`        | `1`            | Only output groups whose count >= N      |
| `-h / --help`          | —              | Print usage to stdout and exit `0`       |

Unknown flags cause exit `1` with a usage hint on stderr.

### Exit codes

| Code | Meaning                                                       |
|------|---------------------------------------------------------------|
| `0`  | Success (warnings may have been emitted to stderr)            |
| `1`  | Bad arguments (unknown flag, missing required value)          |
| `2`  | I/O error (input file unreadable, output path unwritable)     |
| `3`  | Unrecoverable parse error (required header columns missing)   |

---

## 8. Out of scope

The following are explicitly **not** part of this tool:

- Grouping or deduplication by `message` content
- Streaming / tail-follow / watch mode
- Timezone conversion (timestamps are written back verbatim in their original format)
- Configuration files or environment-variable overrides for defaults
- Output formats other than CSV (no JSON, TSV, Parquet, etc.)
- Log-level hierarchy or roll-up (e.g. treating `WARN` as a subset of `ERROR`)
- Input formats other than comma-separated CSV with a header row

## Signed off
Nina Pyshcheva
Date: 07/05/2026

## Implementation notes
src/logsum.py is implemented