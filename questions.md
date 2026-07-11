# Repo Q&A

---

## Where is the grouping rule?

**Files read:** `spec.md`, `src/logsum.py`

The rule is defined in `spec.md` (§1, line 9) and implemented in `src/logsum.py`.

The spec states each unique `(service, level)` pair — both values taken **after normalisation** — defines one output row (`spec.md:9-11`).

In the implementation, each row's service and level are normalised first (strip + lowercase for service, strip + uppercase for level, with blank level becoming `"UNKNOWN"`), then the tuple `(svc, level)` is used as the dict key (`src/logsum.py:70`). A new group entry is created on first sight (`src/logsum.py:71-72`); subsequent rows with the same key increment the existing group's count and update its time range (`src/logsum.py:74-79`). The final output is built by iterating `groups.items()` (`src/logsum.py:81-90`).

**Could not verify:** output row ordering — `groups` is a plain `dict` so iteration order is insertion order, but the spec does not guarantee any ordering (`spec.md` §3 is silent on this).

---

## How is missing level handled?

**Files read:** `spec.md`, `src/logsum.py`

The spec says a row whose `level` cell is absent or blank is normalised to the sentinel `"UNKNOWN"`, still counted, still participates in `first_seen`/`last_seen`, and triggers one `WARNING` line on stderr per affected row (`spec.md:46-52`).

The implementation reads the raw level, strips whitespace, and checks if the result is falsy (`src/logsum.py:53, 57`). If so, `level` is set to `"UNKNOWN"` and the warning `WARNING: row <n>: missing level, using "UNKNOWN"` is printed to stderr (`src/logsum.py:57, 60-61`). The row number `n` counts from `2` because `enumerate(reader, start=2)` treats the header as row 1 (`src/logsum.py:52`). The row is then grouped and counted normally alongside rows with valid levels (`src/logsum.py:70-79`).

**Could not verify:** nothing — behaviour matches spec exactly.

---

## How do I run tests and CI locally?

**Files read:** `CLAUDE.md`, `.github/workflows/ci.yml`

**Tests:**

```
pip install pytest ruff
pytest -v
```

`CLAUDE.md:15-16` specifies Python 3.11, ruff for lint, and pytest for tests. There are no third-party runtime dependencies — only the stdlib is used at runtime (`CLAUDE.md:14`).

To also lint before testing (matching CI exactly):

```
ruff check .
pytest -v
```

**CI workflow** (`.github/workflows/ci.yml`):

The workflow triggers on every `push` and `pull_request` (`.github/workflows/ci.yml:3-5`), runs on `ubuntu-latest` (`.github/workflows/ci.yml:9`), installs `ruff` and `pytest` via `pip` (`.github/workflows/ci.yml:16`), then runs `ruff check .` followed by `pytest -v` (`.github/workflows/ci.yml:19, 22`). No Docker, no secrets, no extra services.

To replicate the CI environment locally as closely as possible, use Python 3.11 specifically — that is the only pinned version (`.github/workflows/ci.yml:13`).

**Could not verify:** whether a `requirements.txt` or `pyproject.toml` exists that would change the install step — the repo has neither, so `pip install ruff pytest` is the complete install.

## Verification
Done
