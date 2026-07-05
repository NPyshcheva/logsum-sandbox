# Test notes

## Coverage gaps to watch

- **Warning row numbers** — the spec defines the warning format as `WARNING: row <n>: ...` but does not say whether `n` is the CSV file line number (header = 1) or a 1-indexed data-row counter. Tests verify format and per-row count but do not assert the exact value of `n`. If the numbering is ever pinned in the spec, add explicit assertions.

- **Timestamp formats beyond `Z` suffix** — the spec shows only the `YYYY-MM-DDTHH:MM:SSZ` form. Tests do not cover other technically valid ISO 8601 representations (e.g. `2024-01-01T10:00:00+00:00`). If the spec is extended to accept offset notation, add normalisation tests.

- **Blank `service` after stripping** — the spec defines a sentinel only for missing `level` (`UNKNOWN`). Behaviour when `service` is empty or whitespace-only is unspecified. No tests cover this case; add them if the spec is updated.

- **Required header columns** — the spec says exit 3 when "required header columns" are missing but does not list them by name. Tests use a completely unrelated header to trigger exit 3. If the tool requires a strict subset (e.g. `timestamp` + `service` + `level` but not `message`), edge cases like a header that has only some required columns are untested.

- **Output row order** — the spec does not guarantee any ordering of output rows. Tests that check multiple rows sort before comparing. If a deterministic order is ever specified, the sort calls should be removed and order assertions added.
