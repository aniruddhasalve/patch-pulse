# Patch Pulse

Patch Pulse is a dependency-free Python CLI that turns a unified diff into a small, explainable risk pulse. It flags sensitive files, tells you whether tests changed, and exposes a stable score for lightweight CI gates.

## Quick start

```bash
python3 patch_pulse.py changes.diff
cat changes.diff | python3 patch_pulse.py --json
```

Use `--fail-above N` to make CI fail when the score is at least `N`:

```bash
git diff origin/main...HEAD | python3 patch_pulse.py --fail-above 60
```

Use `--sarif` to emit SARIF 2.1.0 with a risk result and affected-file locations for GitHub code scanning or other CI dashboards:

```bash
git diff origin/main...HEAD | python3 patch_pulse.py --sarif > patch-pulse.sarif
```

Example human output:

```text
MEDIUM risk (31/100)
3 files, +18/-4, 4 hunks
Tests touched: yes
```

The score is intentionally transparent: changed lines + hunk weight + sensitive-file and public-interface signals. It is a signal, not a replacement for review.

## Test

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT
