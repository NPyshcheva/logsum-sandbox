"""Aggregate events.csv into one summary row per (service, level) group."""

import argparse
import csv
import sys
from datetime import datetime, timezone

_TS_FMT   = "%Y-%m-%dT%H:%M:%SZ"
_REQUIRED = {"timestamp", "level", "service", "message"}
_OUT_COLS = ["service", "level", "count", "first_seen", "last_seen"]


class _Parser(argparse.ArgumentParser):
    def error(self, message):          # exit 1 for bad args (argparse default is 2)
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        sys.exit(1)


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.strptime(raw, _TS_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _aggregate(path: str) -> list[dict]:
    try:
        fh = open(path, newline="", encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    with fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            print("ERROR: input file has no header row", file=sys.stderr)
            sys.exit(3)

        # normalise header names so column order AND case don't matter
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
        missing_cols = _REQUIRED - set(reader.fieldnames)
        if missing_cols:
            print(
                f"ERROR: missing required columns: {', '.join(sorted(missing_cols))}",
                file=sys.stderr,
            )
            sys.exit(3)

        groups: dict[tuple, dict] = {}

        for n, row in enumerate(reader, start=2):
            raw_level = (row.get("level")     or "").strip()
            raw_svc   = (row.get("service")   or "").strip()
            raw_ts    = (row.get("timestamp") or "").strip()

            level = raw_level.upper() if raw_level else "UNKNOWN"
            svc   = raw_svc.lower()

            if not raw_level:
                print(f'WARNING: row {n}: missing level, using "UNKNOWN"', file=sys.stderr)

            ts = _parse_ts(raw_ts) if raw_ts else None
            if raw_ts and ts is None:
                print(
                    f'WARNING: row {n}: cannot parse timestamp "{raw_ts}", excluded from time range',
                    file=sys.stderr,
                )

            key = (svc, level)
            if key not in groups:
                groups[key] = {"count": 0, "first": None, "last": None}
            g = groups[key]
            g["count"] += 1
            if ts is not None:
                if g["first"] is None or ts < g["first"]:
                    g["first"] = ts
                if g["last"] is None or ts > g["last"]:
                    g["last"] = ts

    return [
        {
            "service":    svc,
            "level":      level,
            "count":      g["count"],
            "first_seen": g["first"].strftime(_TS_FMT) if g["first"] else "",
            "last_seen":  g["last"].strftime(_TS_FMT)  if g["last"]  else "",
        }
        for (svc, level), g in groups.items()
    ]


def _write(path: str, rows: list[dict]) -> None:
    try:
        fh = open(path, "w", newline="", encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    with fh:
        w = csv.DictWriter(fh, fieldnames=_OUT_COLS)
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    p = _Parser(prog="logsum", description="Aggregate events.csv per (service, level).")
    p.add_argument("input_pos",  nargs="?", metavar="INPUT",  help="input CSV  (default: events.csv)")
    p.add_argument("output_pos", nargs="?", metavar="OUTPUT", help="output CSV (default: summary.csv)")
    p.add_argument("-i", "--input",  metavar="PATH", help="input CSV path")
    p.add_argument("-o", "--output", metavar="PATH", help="output CSV path")
    args = p.parse_args(argv)

    src = args.input  or args.input_pos  or "events.csv"
    dst = args.output or args.output_pos or "summary.csv"
    _write(dst, _aggregate(src))


if __name__ == "__main__":
    main()
