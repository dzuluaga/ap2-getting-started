"""Scaffold a new lesson folder from lessons/_template.

Usage: python scripts/new-lesson.py <number> <slug> [--lessons-dir DIR]
Example: python scripts/new-lesson.py 03 selective-disclosure
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("number", help="Two-digit lesson number, e.g. 03")
    parser.add_argument("slug", help="kebab-case slug, e.g. selective-disclosure")
    parser.add_argument(
        "--lessons-dir",
        default=str(Path(__file__).resolve().parents[1] / "lessons"),
    )
    args = parser.parse_args()

    lessons_dir = Path(args.lessons_dir)
    template = lessons_dir / "_template"
    dest = lessons_dir / f"{args.number}-{args.slug}"
    if dest.exists():
        raise SystemExit(f"{dest} already exists")
    shutil.copytree(template, dest)
    print(f"Created {dest}")


if __name__ == "__main__":
    main()
