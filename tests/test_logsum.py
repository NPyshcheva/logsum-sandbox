"""
pytest tests for src/logsum.py — derived from spec.md only; source not read.

Sections covered:
  1  Grouping
  2  Normalisation (level, service, timestamp, column-order)
  3  Output columns (names, order, count, first_seen, last_seen, format)
  4  Missing level  → UNKNOWN sentinel + stderr WARNING
  5  Malformed timestamp → counted but excluded from time range + WARNING
  6  Empty / bad input  → correct exit codes and output
  7  CLI flags and exit codes
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).parent.parent / "src" / "logsum.py"
FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

_HEADER = ["timestamp", "service", "level", "message"]
OUTPUT_COLS = ["service", "level", "count", "first_seen", "last_seen"]

TS1 = "2024-01-01T10:00:00Z"   # earliest
TS2 = "2024-01-02T11:00:00Z"   # middle
TS3 = "2024-01-03T12:00:00Z"   # latest

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(*args, cwd=None):
    """Invoke the CLI and return the completed process."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def write_csv(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        csv.writer(fh).writerows(rows)


def read_csv(path: Path) -> list:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def read_header(path: Path) -> list:
    with open(path, newline="") as fh:
        return next(csv.reader(fh))


def sorted_rows(rows: list) -> list:
    return sorted(rows, key=lambda r: (r["service"], r["level"]))


def warning_lines(stderr: str, keyword: str) -> list:
    return [ln for ln in stderr.splitlines() if keyword in ln]


# ===========================================================================
# Section 1 — Grouping
# ===========================================================================


class TestGrouping:
    def test_two_rows_same_key_merged_into_one(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "auth", "ERROR", "msg1"],
            [TS2, "auth", "ERROR", "msg2"],
        ])
        result = run("-i", str(inp), "-o", str(out))
        assert result.returncode == 0
        rows = read_csv(out)
        assert len(rows) == 1
        assert rows[0]["service"] == "auth"
        assert rows[0]["level"] == "ERROR"
        assert rows[0]["count"] == "2"

    def test_different_services_give_separate_rows(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "auth", "ERROR", "m"],
            [TS1, "gateway", "ERROR", "m"],
        ])
        result = run("-i", str(inp), "-o", str(out))
        assert result.returncode == 0
        services = {r["service"] for r in read_csv(out)}
        assert services == {"auth", "gateway"}

    def test_different_levels_give_separate_rows(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "auth", "ERROR", "m"],
            [TS1, "auth", "WARN", "m"],
        ])
        result = run("-i", str(inp), "-o", str(out))
        assert result.returncode == 0
        assert len(read_csv(out)) == 2

    def test_count_per_group_is_correct(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "auth", "ERROR", "m"],
            [TS2, "auth", "WARN", "m"],
            [TS1, "gateway", "ERROR", "m"],
            [TS2, "auth", "ERROR", "m"],
            [TS3, "auth", "ERROR", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        rows = sorted_rows(read_csv(out))
        assert len(rows) == 3
        auth_err = next(r for r in rows if r["service"] == "auth" and r["level"] == "ERROR")
        assert auth_err["count"] == "3"
        auth_warn = next(r for r in rows if r["service"] == "auth" and r["level"] == "WARN")
        assert auth_warn["count"] == "1"

    def test_grouping_uses_post_normalisation_values(self, tmp_path):
        """Rows that differ only in raw whitespace/case share the same group."""
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, " Auth ", " error ", "m"],
            [TS2, "auth", "ERROR", "m"],
        ])
        result = run("-i", str(inp), "-o", str(out))
        assert result.returncode == 0
        rows = read_csv(out)
        assert len(rows) == 1
        assert rows[0]["count"] == "2"


# ===========================================================================
# Section 2 — Normalisation
# ===========================================================================


class TestNormalisation:
    def test_level_trailing_whitespace_stripped_and_uppercased(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "warn ", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["level"] == "WARN"

    def test_level_leading_whitespace_stripped_and_uppercased(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "  ERROR", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["level"] == "ERROR"

    def test_level_mixed_case_uppercased(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "Warning", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["level"] == "WARNING"

    def test_service_trailing_whitespace_stripped_and_lowercased(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, " Auth ", "INFO", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["service"] == "auth"

    def test_service_mixed_case_lowercased(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "MyService", "INFO", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["service"] == "myservice"

    def test_timestamp_surrounding_whitespace_stripped_before_parsing(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [" 2024-01-02T10:00:00Z ", "svc", "INFO", "m"]])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["first_seen"] == "2024-01-02T10:00:00Z"
        assert row["last_seen"] == "2024-01-02T10:00:00Z"

    def test_column_order_irrelevant(self, tmp_path):
        """Tool reads by header name; any column order in input is accepted."""
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            ["message", "level", "timestamp", "service"],
            ["msg", "INFO", TS1, "svc"],
        ])
        result = run("-i", str(inp), "-o", str(out))
        assert result.returncode == 0
        row = read_csv(out)[0]
        assert row["service"] == "svc"
        assert row["level"] == "INFO"
        assert row["first_seen"] == TS1


# ===========================================================================
# Section 3 — Output columns
# ===========================================================================


class TestOutputColumns:
    def test_output_column_names_and_order(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_header(out) == OUTPUT_COLS

    def test_count_is_correct_integer(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "svc", "INFO", "m"],
            [TS2, "svc", "INFO", "m"],
            [TS3, "svc", "INFO", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["count"] == "3"
        assert int(row["count"]) == 3

    def test_first_seen_is_earliest_valid_timestamp(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS3, "svc", "INFO", "m"],
            [TS1, "svc", "INFO", "m"],
            [TS2, "svc", "INFO", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["first_seen"] == TS1

    def test_last_seen_is_latest_valid_timestamp(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "svc", "INFO", "m"],
            [TS3, "svc", "INFO", "m"],
            [TS2, "svc", "INFO", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["last_seen"] == TS3

    def test_first_seen_and_last_seen_same_when_one_row(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS2, "svc", "INFO", "m"]])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["first_seen"] == TS2
        assert row["last_seen"] == TS2

    def test_output_timestamps_match_required_format(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert _TS_RE.match(row["first_seen"]), f"bad format: {row['first_seen']!r}"
        assert _TS_RE.match(row["last_seen"]), f"bad format: {row['last_seen']!r}"

    def test_message_column_not_in_output(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "some message"]])
        run("-i", str(inp), "-o", str(out))
        assert "message" not in read_csv(out)[0]

    def test_all_malformed_timestamps_write_empty_time_fields(self, tmp_path):
        """When every row in a group has a bad timestamp both fields are empty."""
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            ["not-a-date", "svc", "ERROR", "m"],
            ["also-bad",   "svc", "ERROR", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["first_seen"] == ""
        assert row["last_seen"] == ""

    def test_independent_time_ranges_per_group(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "a", "ERROR", "m"],
            [TS3, "a", "ERROR", "m"],
            [TS2, "b", "WARN",  "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        rows = {r["service"]: r for r in read_csv(out)}
        assert rows["a"]["first_seen"] == TS1
        assert rows["a"]["last_seen"] == TS3
        assert rows["b"]["first_seen"] == TS2
        assert rows["b"]["last_seen"] == TS2


# ===========================================================================
# Section 4 — Missing level
# ===========================================================================


class TestMissingLevel:
    def test_blank_level_normalised_to_unknown(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["level"] == "UNKNOWN"

    def test_whitespace_only_level_normalised_to_unknown(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "   ", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["level"] == "UNKNOWN"

    def test_missing_level_row_still_counted(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "svc", "", "m"],
            [TS2, "svc", "", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["count"] == "2"

    def test_missing_level_row_participates_in_time_range(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS2, "svc", "", "m"]])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["first_seen"] == TS2
        assert row["last_seen"] == TS2

    def test_warning_written_to_stderr_for_missing_level(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "", "m"]])
        result = run("-i", str(inp), "-o", str(out))
        assert "missing level" in result.stderr
        assert '"UNKNOWN"' in result.stderr

    def test_warning_format_for_missing_level(self, tmp_path):
        """Each warning must match: WARNING: row <n>: missing level, using "UNKNOWN"."""
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "", "m"]])
        result = run("-i", str(inp), "-o", str(out))
        pattern = re.compile(r'WARNING: row \d+: missing level, using "UNKNOWN"')
        assert any(pattern.search(ln) for ln in result.stderr.splitlines())

    def test_one_warning_per_affected_row(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "svc", "",     "m"],   # affected
            [TS2, "svc", "",     "m"],   # affected
            [TS3, "svc", "INFO", "m"],   # not affected
        ])
        result = run("-i", str(inp), "-o", str(out))
        assert len(warning_lines(result.stderr, "missing level")) == 2

    def test_missing_level_exits_0(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "", "m"]])
        assert run("-i", str(inp), "-o", str(out)).returncode == 0

    def test_unknown_group_mixed_with_named_levels(self, tmp_path):
        """UNKNOWN rows form their own group, not merged with named-level groups."""
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1, "svc", "",      "m"],
            [TS2, "svc", "ERROR", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        levels = {r["level"] for r in read_csv(out)}
        assert "UNKNOWN" in levels
        assert "ERROR" in levels
        assert len(levels) == 2


# ===========================================================================
# Section 5 — Malformed timestamp
# ===========================================================================


class TestMalformedTimestamp:
    def test_malformed_ts_row_still_counted(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            ["not-a-date", "svc", "INFO", "m"],
            [TS1,          "svc", "INFO", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out)[0]["count"] == "2"

    def test_malformed_ts_excluded_from_time_range(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            ["not-a-date", "svc", "INFO", "m"],
            [TS2,          "svc", "INFO", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["first_seen"] == TS2
        assert row["last_seen"] == TS2

    def test_malformed_ts_warning_on_stderr(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, ["BADTS", "svc", "INFO", "m"]])
        result = run("-i", str(inp), "-o", str(out))
        assert "cannot parse timestamp" in result.stderr
        assert "BADTS" in result.stderr
        assert "excluded from time range" in result.stderr

    def test_warning_format_for_malformed_ts(self, tmp_path):
        """Must match: WARNING: row <n>: cannot parse timestamp "<value>", excluded from time range."""
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, ["BADTS", "svc", "INFO", "m"]])
        result = run("-i", str(inp), "-o", str(out))
        pattern = re.compile(
            r'WARNING: row \d+: cannot parse timestamp "BADTS", excluded from time range'
        )
        assert any(pattern.search(ln) for ln in result.stderr.splitlines())

    def test_one_warning_per_malformed_row(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            ["BAD1", "svc", "INFO", "m"],
            ["BAD2", "svc", "INFO", "m"],
            [TS1,    "svc", "INFO", "m"],
        ])
        result = run("-i", str(inp), "-o", str(out))
        assert len(warning_lines(result.stderr, "cannot parse timestamp")) == 2

    def test_warning_contains_exact_bad_value(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, ["THIS_IS_GARBAGE", "svc", "INFO", "m"]])
        result = run("-i", str(inp), "-o", str(out))
        assert "THIS_IS_GARBAGE" in result.stderr

    def test_all_malformed_ts_empty_time_fields(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            ["bad1", "svc", "ERROR", "m"],
            ["bad2", "svc", "ERROR", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["first_seen"] == ""
        assert row["last_seen"] == ""

    def test_partial_malformed_uses_only_valid_timestamps(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            [TS1,    "svc", "ERROR", "m"],
            ["bad",  "svc", "ERROR", "m"],
            [TS3,    "svc", "ERROR", "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        row = read_csv(out)[0]
        assert row["first_seen"] == TS1
        assert row["last_seen"] == TS3
        assert row["count"] == "3"

    def test_malformed_ts_does_not_pollute_other_group(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [
            _HEADER,
            ["bad",  "svc", "ERROR", "m"],
            [TS1,    "svc", "INFO",  "m"],
        ])
        run("-i", str(inp), "-o", str(out))
        rows = {r["level"]: r for r in read_csv(out)}
        assert rows["INFO"]["first_seen"] == TS1
        assert rows["ERROR"]["first_seen"] == ""

    def test_malformed_ts_exits_0(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, ["bad", "svc", "INFO", "m"]])
        assert run("-i", str(inp), "-o", str(out)).returncode == 0


# ===========================================================================
# Section 6 — Empty / bad input
# ===========================================================================


class TestEmptyInput:
    def test_missing_file_exits_2(self, tmp_path):
        result = run("-i", str(tmp_path / "does_not_exist.csv"),
                     "-o", str(tmp_path / "out.csv"))
        assert result.returncode == 2

    def test_missing_file_writes_message_to_stderr(self, tmp_path):
        result = run("-i", str(tmp_path / "does_not_exist.csv"),
                     "-o", str(tmp_path / "out.csv"))
        assert result.stderr.strip() != ""

    def test_header_only_file_exits_0(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER])
        assert run("-i", str(inp), "-o", str(out)).returncode == 0

    def test_header_only_file_writes_header_only_output(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER])
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out) == []
        assert read_header(out) == OUTPUT_COLS

    def test_header_plus_blank_lines_exits_0(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        inp.write_text(",".join(_HEADER) + "\n\n\n\n")
        assert run("-i", str(inp), "-o", str(out)).returncode == 0

    def test_header_plus_blank_lines_writes_header_only_output(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        inp.write_text(",".join(_HEADER) + "\n\n\n\n")
        run("-i", str(inp), "-o", str(out))
        assert read_csv(out) == []
        assert read_header(out) == OUTPUT_COLS

    def test_missing_required_columns_in_header_exits_3(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        inp.write_text("col_a,col_b,col_c\nval1,val2,val3\n")
        assert run("-i", str(inp), "-o", str(out)).returncode == 3

    def test_missing_required_columns_writes_message_to_stderr(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        inp.write_text("col_a,col_b,col_c\nval1,val2,val3\n")
        result = run("-i", str(inp), "-o", str(out))
        assert result.stderr.strip() != ""

    def test_completely_empty_file_exits_3(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        inp.write_text("")
        assert run("-i", str(inp), "-o", str(out)).returncode == 3

    def test_completely_empty_file_writes_message_to_stderr(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        inp.write_text("")
        result = run("-i", str(inp), "-o", str(out))
        assert result.stderr.strip() != ""

    def test_unwritable_output_path_exits_2(self, tmp_path):
        inp = tmp_path / "events.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        out = tmp_path / "nonexistent_dir" / "summary.csv"
        result = run("-i", str(inp), "-o", str(out))
        assert result.returncode == 2


# ===========================================================================
# Section 7 — CLI flags and exit codes
# ===========================================================================


class TestCLI:
    # --- default paths ---

    def test_default_input_is_events_csv(self, tmp_path):
        (tmp_path / "events.csv").write_text(
            ",".join(_HEADER) + "\n" + f"{TS1},svc,INFO,msg\n"
        )
        result = run("-o", str(tmp_path / "summary.csv"), cwd=tmp_path)
        assert result.returncode == 0

    def test_default_output_is_summary_csv(self, tmp_path):
        (tmp_path / "events.csv").write_text(
            ",".join(_HEADER) + "\n" + f"{TS1},svc,INFO,msg\n"
        )
        run(cwd=tmp_path)
        assert (tmp_path / "summary.csv").exists()

    # --- -i / --input ---

    def test_short_input_flag(self, tmp_path):
        inp, out = tmp_path / "custom_in.csv", tmp_path / "custom_out.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        assert run("-i", str(inp), "-o", str(out)).returncode == 0

    def test_long_input_flag(self, tmp_path):
        inp, out = tmp_path / "custom_in.csv", tmp_path / "custom_out.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        assert run("--input", str(inp), "--output", str(out)).returncode == 0

    # --- -o / --output ---

    def test_short_output_flag_creates_named_file(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "my_out.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        run("-i", str(inp), "-o", str(out))
        assert out.exists()

    def test_long_output_flag_creates_named_file(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "my_out.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        run("-i", str(inp), "--output", str(out))
        assert out.exists()

    # --- -h / --help ---

    def test_help_short_flag_exits_0(self):
        assert run("-h").returncode == 0

    def test_help_long_flag_exits_0(self):
        assert run("--help").returncode == 0

    def test_help_short_flag_prints_to_stdout(self):
        assert run("-h").stdout.strip() != ""

    def test_help_long_flag_prints_to_stdout(self):
        assert run("--help").stdout.strip() != ""

    def test_help_writes_nothing_to_stderr(self):
        assert run("-h").stderr == ""

    # --- unknown flags ---

    def test_unknown_flag_exits_1(self):
        assert run("--this-flag-does-not-exist").returncode == 1

    def test_unknown_flag_writes_usage_hint_to_stderr(self):
        result = run("--this-flag-does-not-exist")
        assert result.stderr.strip() != ""

    def test_unknown_short_flag_exits_1(self):
        assert run("-Z").returncode == 1

    # --- exit-code summary ---

    def test_success_exits_0(self, tmp_path):
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, [TS1, "svc", "INFO", "m"]])
        assert run("-i", str(inp), "-o", str(out)).returncode == 0

    def test_warnings_do_not_change_exit_0(self, tmp_path):
        """Both missing-level and bad-timestamp warnings still yield exit 0."""
        inp, out = tmp_path / "events.csv", tmp_path / "summary.csv"
        write_csv(inp, [_HEADER, ["bad-ts", "svc", "", "m"]])
        assert run("-i", str(inp), "-o", str(out)).returncode == 0


# ===========================================================================
# Fixture-based integration tests
# ===========================================================================


class TestWithFixtures:
    """End-to-end tests that drive the CLI against the static fixture files."""

    def test_simple_produces_correct_groups(self, tmp_path):
        out = tmp_path / "summary.csv"
        result = run("-i", str(FIXTURES / "simple.csv"), "-o", str(out))
        assert result.returncode == 0
        rows = sorted_rows(read_csv(out))
        assert len(rows) == 2
        assert rows[0]["service"] == "auth"
        assert rows[0]["level"] == "ERROR"
        assert rows[0]["count"] == "2"
        assert rows[1]["service"] == "gateway"
        assert rows[1]["level"] == "WARN"
        assert rows[1]["count"] == "1"

    def test_simple_first_last_seen(self, tmp_path):
        out = tmp_path / "summary.csv"
        run("-i", str(FIXTURES / "simple.csv"), "-o", str(out))
        rows = {r["service"]: r for r in read_csv(out)}
        assert rows["auth"]["first_seen"] == TS1
        assert rows["auth"]["last_seen"] == TS2

    def test_whitespace_fields_normalised(self, tmp_path):
        out = tmp_path / "summary.csv"
        run("-i", str(FIXTURES / "whitespace_fields.csv"), "-o", str(out))
        row = read_csv(out)[0]
        assert row["service"] == "auth"
        assert row["level"] == "WARN"
        assert row["first_seen"] == "2024-01-02T10:00:00Z"

    def test_missing_level_fixture(self, tmp_path):
        out = tmp_path / "summary.csv"
        result = run("-i", str(FIXTURES / "missing_level.csv"), "-o", str(out))
        assert result.returncode == 0
        rows = {r["level"]: r for r in read_csv(out)}
        assert "UNKNOWN" in rows
        assert rows["UNKNOWN"]["count"] == "2"
        assert len(warning_lines(result.stderr, "missing level")) == 2

    def test_malformed_ts_fixture(self, tmp_path):
        out = tmp_path / "summary.csv"
        result = run("-i", str(FIXTURES / "malformed_ts.csv"), "-o", str(out))
        assert result.returncode == 0
        row = read_csv(out)[0]
        assert row["count"] == "2"
        assert row["first_seen"] == TS2
        assert row["last_seen"] == TS2
        assert len(warning_lines(result.stderr, "cannot parse timestamp")) == 1

    def test_all_malformed_ts_fixture(self, tmp_path):
        out = tmp_path / "summary.csv"
        run("-i", str(FIXTURES / "all_malformed_ts.csv"), "-o", str(out))
        row = read_csv(out)[0]
        assert row["count"] == "2"
        assert row["first_seen"] == ""
        assert row["last_seen"] == ""

    def test_header_only_fixture(self, tmp_path):
        out = tmp_path / "summary.csv"
        result = run("-i", str(FIXTURES / "header_only.csv"), "-o", str(out))
        assert result.returncode == 0
        assert read_csv(out) == []
        assert read_header(out) == OUTPUT_COLS

    def test_no_header_fixture_exits_3(self, tmp_path):
        out = tmp_path / "summary.csv"
        result = run("-i", str(FIXTURES / "no_header.csv"), "-o", str(out))
        assert result.returncode == 3
