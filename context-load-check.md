Summary for the rule file **`CLAUDE.md`**.

**Project context**

* The project is a tiny Python CLI that summarizes synthetic `events.csv` logs and produces concise summary reports.

**Conventions**

* Store application code in `src/`.
* Store tests in `tests/`.
* Store sample datasets in `data/`.
* Keep the codebase organized and maintainable.

**Utilities to prefer**

* Python 3.11 standard library
* `ruff`
* `pytest`

**Escalation gates**

* Stop and ask before adding new dependencies.
* Use only synthetic data.
* Never overwrite `spec.md` after sign-off without asking.

**Filename:** `CLAUDE.md`
