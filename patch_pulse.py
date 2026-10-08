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


def _paths(diff: str) -> list[str]:
    return [match.group(2) for line in diff.splitlines() if (match := _FILE_RE.match(line))]


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


def to_sarif(diff: str, pulse: Pulse) -> dict:
    """Build SARIF 2.1.0 without changing the existing JSON contract."""
    sarif_level = {"high": "error", "medium": "warning", "low": "note"}[pulse.level]
    result = {
        "ruleId": "patch-pulse-risk",
        "level": sarif_level,
        "message": {"text": f"{pulse.level.upper()} risk ({pulse.score}/100) across {pulse.files} file(s)."},
        "properties": {
            "score": pulse.score,
            "riskLevel": pulse.level,
            "testsTouched": pulse.tests_touched,
            "sensitiveFiles": pulse.sensitive_files,
        },
        "locations": [
            {"physicalLocation": {"artifactLocation": {"uri": path}}}
            for path in _paths(diff)
        ],
    }
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "Patch Pulse", "informationUri": "https://github.com/aniruddhasalve/patch-pulse"}},
            "results": [result],
        }],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score risk signals in a unified diff")
    parser.add_argument("diff", nargs="?", help="diff file; reads stdin when omitted")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--sarif", action="store_true", help="emit SARIF 2.1.0 for code scanning")
    parser.add_argument("--fail-above", type=int, metavar="N", help="exit 1 when the score is at least N")
    args = parser.parse_args(argv)
    text = Path(args.diff).read_text() if args.diff else sys.stdin.read()
    pulse = analyze(text)
    if args.sarif:
        print(json.dumps(to_sarif(text, pulse), sort_keys=True))
    elif args.json:
        print(json.dumps(asdict(pulse), sort_keys=True))
    else:
        print(f"{pulse.level.upper()} risk ({pulse.score}/100)")
        print(f"{pulse.files} files, +{pulse.additions}/-{pulse.deletions}, {pulse.hunks} hunks")
        print(f"Tests touched: {'yes' if pulse.tests_touched else 'no'}")
        if pulse.sensitive_files:
            print("Sensitive files: " + ", ".join(pulse.sensitive_files))
    return int(args.fail_above is not None and pulse.score >= args.fail_above)


if __name__ == "__main__":
    raise SystemExit(main())
