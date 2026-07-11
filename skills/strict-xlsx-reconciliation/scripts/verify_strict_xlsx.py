#!/usr/bin/env python3
"""Verify an output workbook retained the visual shell of its upstream template."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile


ERROR_TEXT = re.compile(r"#REF!|#DIV/0!|#VALUE!|#NAME\?|#N/A")


def member_hash(path: Path, member: str) -> str:
    with ZipFile(path) as archive:
        return hashlib.sha256(archive.read(member)).hexdigest()


def member_text(path: Path, member: str) -> str:
    with ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")


def fragment(xml: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}\\b[\\s\\S]*?</{tag}>|<{tag}\\b[^>]*/>", xml)
    return match.group(0) if match else None


def row_breaks(xml: str) -> list[int]:
    section = fragment(xml, "rowBreaks") or ""
    return [int(value) for value in re.findall(r'<brk\\b[^>]*\\bid="(\\d+)"', section)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sheet-member", default="xl/worksheets/sheet1.xml")
    parser.add_argument("--inserted-rows", type=int, default=0)
    parser.add_argument("--last-data-row", type=int)
    args = parser.parse_args()
    failures: list[str] = []
    if not args.original.exists() or not args.output.exists():
        missing = [str(path) for path in (args.original, args.output) if not path.exists()]
        print(json.dumps({"ok": False, "failures": [f"Missing: {', '.join(missing)}"]}, ensure_ascii=False))
        return 1
    try:
        for member in ("xl/styles.xml", "xl/theme/theme1.xml"):
            if member_hash(args.original, member) != member_hash(args.output, member):
                failures.append(f"{member} differs")
        original_xml = member_text(args.original, args.sheet_member)
        output_xml = member_text(args.output, args.sheet_member)
    except Exception as error:
        print(json.dumps({"ok": False, "failures": [f"Invalid workbook package: {error}"]}, ensure_ascii=False))
        return 1
    for tag in ("cols", "sheetViews", "pageSetup", "printOptions", "pageMargins"):
        if fragment(original_xml, tag) != fragment(output_xml, tag):
            failures.append(f"{tag} differs")
    original_breaks = row_breaks(original_xml)
    output_breaks = row_breaks(output_xml)
    if args.inserted_rows:
        cutoff = args.last_data_row or 0
        expected = [value + args.inserted_rows if value >= cutoff else value for value in original_breaks]
    else:
        expected = original_breaks
    if output_breaks != expected:
        failures.append(f"row breaks differ: expected {expected}, got {output_breaks}")
    if ERROR_TEXT.search(output_xml):
        failures.append("formula error text found")
    print(json.dumps({"ok": not failures, "failures": failures, "row_breaks": output_breaks}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
