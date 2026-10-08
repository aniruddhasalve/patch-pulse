# Patch Pulse

Patch Pulse is a dependency-free Python CLI that turns a unified diff into a small, explainable risk pulse. It flags sensitive files, tells you whether tests changed, and exposes a stable score for lightweight CI gates.

## Quick start

```bash
python3 patch_pulse.py changes.diff
cat changes.diff | python3 patch_pulse.py --json
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
