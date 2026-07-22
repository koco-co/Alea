#!/usr/bin/env python3
"""Report repository hygiene issues; delete only unambiguous generated output."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

SAFE_GENERATED = (
    ".tmp",
    "playwright-report",
    "test-results",
    "web/playwright-report",
    "web/test-results",
    "tests/e2e/playwright-report",
    "tests/e2e/test-results",
)
REVIEW_ONLY = (
    "Web-Prototype.zip",
    "docs/qa/reports/2026-07-21-design-qa-superseded.md",
    "SUPPORT.md",
    "THIRD_PARTY_REFERENCES.md",
    "docs/evidence",
    "PrototypeDesign/.od-skills",
)


def tracked(root: Path, relative: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="remove safe generated output")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    failures = 0
    print("safe generated artifacts:")
    for relative in SAFE_GENERATED:
        path = root / relative
        state = "absent"
        if path.exists():
            state = "tracked" if tracked(root, relative) else "untracked"
            if args.fix and state == "untracked":
                shutil.rmtree(path) if path.is_dir() else path.unlink()
                state = "removed"
            elif state == "tracked":
                failures += 1
        print(f"  {relative}: {state}")

    print("manual-review assets (never auto-deleted):")
    for relative in REVIEW_ONLY:
        path = root / relative
        print(f"  {relative}: {'present' if path.exists() else 'absent'}")

    if failures:
        print("tracked generated artifacts must be removed with git rm after review")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
