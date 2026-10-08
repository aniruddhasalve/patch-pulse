"""Deterministic risk signals for unified diffs."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_FILE_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_HUNK_RE = re.compile(r"^@@")
_SENSITIVE_RE = re.compile(r"(^|/)(\.env|secrets?|credentials?|.*\.pem)$", re.I)
_TEST_RE = re.compile(r"(^|/)(test_|tests?/|.*(_test|\.spec))", re.I)
_BREAKING_RE = re.compile(r"^[-+]\s*(public|export|def|class|interface|type|function)\b", re.I)


@dataclass(frozen=True)
class Pulse:
    files: int
    additions: int
    deletions: int
    hunks: int
    sensitive_files: list[str]
    tests_touched: bool
    breaking_lines: int
    score: int
    level: str


def analyze(diff: str) -> Pulse:
    files: list[str] = []
    additions = deletions = hunks = breaking_lines = 0
    tests_touched = False
    sensitive: list[str] = []

    for line in diff.splitlines():
        match = _FILE_RE.match(line)
        if match:
            path = match.group(2)
            files.append(path)
            tests_touched |= bool(_TEST_RE.search(path))
            if _SENSITIVE_RE.search(path):
                sensitive.append(path)
        elif _HUNK_RE.match(line):
            hunks += 1
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
            breaking_lines += bool(_BREAKING_RE.search(line[1:]))
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
            breaking_lines += bool(_BREAKING_RE.search(line[1:]))

    score = min(100, additions + deletions + (hunks * 3) + (len(sensitive) * 25) + (breaking_lines * 8))
    if sensitive or score >= 60:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"
    return Pulse(len(files), additions, deletions, hunks, sensitive, tests_touched, breaking_lines, score, level)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score risk signals in a unified diff")
    parser.add_argument("diff", nargs="?", help="diff file; reads stdin when omitted")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    text = Path(args.diff).read_text() if args.diff else sys.stdin.read()
    pulse = analyze(text)
    if args.json:
        print(json.dumps(asdict(pulse), sort_keys=True))
    else:
        print(f"{pulse.level.upper()} risk ({pulse.score}/100)")
        print(f"{pulse.files} files, +{pulse.additions}/-{pulse.deletions}, {pulse.hunks} hunks")
        print(f"Tests touched: {'yes' if pulse.tests_touched else 'no'}")
        if pulse.sensitive_files:
            print("Sensitive files: " + ", ".join(pulse.sensitive_files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
