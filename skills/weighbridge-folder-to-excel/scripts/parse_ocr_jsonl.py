#!/usr/bin/env python3
"""Parse OCR JSONL into conservative, reviewable weighbridge rows.

The script intentionally contains no company names, user paths, real plates, or
supplier rules. Keep those values in a local JSON configuration file.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value or "").replace("：", ":").replace("，", ".")


def load_config(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration must be a JSON object")
    return data


def folder_date(folder: Path | None) -> str:
    match = re.search(r"(20\d{2})[-/.年 ]?(\d{1,2})[-/.月 ]?(\d{1,2})", str(folder or ""))
    if match:
        y, month, day = map(int, match.groups())
        return f"{y:04d}-{month:02d}-{day:02d}"
    return ""


def infer_date(text: str, fallback: str) -> str:
    match = re.search(r"(20\d{2})[-/.年 ]?(\d{1,2})[-/.月 ]?(\d{1,2})", text or "")
    if match:
        y, month, day = map(int, match.groups())
        return f"{y:04d}-{month:02d}-{day:02d}"
    return fallback


def normalize_doc(value: str, replacements: dict[str, str]) -> str:
    result = compact(value).upper()
    for wrong, correct in replacements.items():
        result = result.replace(str(wrong).upper(), str(correct).upper())
    return re.sub(r"[^A-Z0-9]", "", result)


def document_candidates(text: str, replacements: dict[str, str]) -> list[str]:
    result: list[str] = []
    patterns = [
        r"(?:序号|序列号|磅单号|单据编号|票据编号)[:：]?([A-Z0-9-]{6,24})",
        r"(?<![A-Z0-9])([A-Z]{2,8}\d{5,20})(?![A-Z0-9])",
    ]
    for pattern in patterns:
        for raw in re.findall(pattern, compact(text).upper()):
            value = normalize_doc(raw, replacements)
            if value and value not in result:
                result.append(value)
    return result


def plate(text: str) -> str:
    candidates = re.findall(r"[\u4e00-\u9fff][A-Z][A-Z0-9]{5,6}(?![A-Z0-9])", compact(text).upper())
    return Counter(candidates).most_common(1)[0][0] if candidates else "待核"


def station(text: str, fallback: str) -> str:
    raw = compact(text)
    for name in ("中心站", "水稳站", "沥青站", "尧山站"):
        if name[:-1] in raw:
            return name
    return fallback


def material(text: str, rules: list[dict[str, Any]]) -> tuple[str, str, str]:
    raw = compact(text)
    for rule in rules:
        pattern = str(rule.get("pattern", ""))
        if pattern and re.search(pattern, raw, re.I):
            return str(rule.get("material", "待核")), str(rule.get("spec", "")), ""
    return "待核", "", "待核：材料/规格 OCR 未确认"


def supplier(text: str, patterns: list[dict[str, Any]]) -> str:
    raw = compact(text)
    for item in patterns:
        pattern = str(item.get("pattern", ""))
        if pattern and re.search(pattern, raw, re.I):
            return str(item.get("supplier", ""))
    return ""


def tons(value: int) -> float:
    return round(value / 1000 if value >= 1000 else value, 2)


def station_weight(text: str) -> tuple[float | None, float | None]:
    numbers = [int(v) for v in re.findall(r"(?<!\d)(\d{5,6})(?!\d)", text)]
    best: tuple[int, int | None, int] | None = None
    for index in range(len(numbers) - 2):
        gross, tare, net = numbers[index : index + 3]
        if gross <= tare or net <= tare:
            continue
        error = abs(gross - tare - net)
        if error <= 1500 and (best is None or error < best[2]):
            delivery = numbers[index + 3] if index + 3 < len(numbers) else None
            best = (net, delivery, error)
    if best is None:
        return None, None
    net, delivery, _ = best
    return tons(net), tons(delivery) if delivery else None


def source_weight(text: str) -> float | None:
    values = [float(v.replace("。", ".")) for v in re.findall(r"(?<!\d)(\d{1,3}[.。]\d{1,3})(?!\d)", text)]
    for index in range(len(values) - 2):
        tare, gross, net = values[index : index + 3]
        if 10 <= tare <= 40 and gross > tare and 10 <= net <= 120 and abs(gross - tare - net) <= 0.1:
            return round(net, 2)
    return None


def consensus(candidates: list[tuple[float, float]]) -> float | None:
    if not candidates:
        return None
    clusters: list[list[tuple[float, float]]] = []
    for value, score in candidates:
        for group in clusters:
            if abs(group[0][0] - value) <= 0.05:
                group.append((value, score))
                break
        else:
            clusters.append([(value, score)])
    winner = max(clusters, key=lambda group: sum(score for _, score in group))
    return max(winner, key=lambda item: item[1])[0]


def parse_record(item: dict[str, Any], folder: Path | None, config: dict[str, Any]) -> dict[str, Any]:
    candidates = sorted(item.get("candidates") or [], key=lambda c: float(c.get("score") or 0), reverse=True)
    texts = [str(candidate.get("text") or "") for candidate in candidates]
    joined = "\n".join(texts)
    replacements = dict(config.get("document_prefix_replacements") or {})
    docs: list[str] = []
    station_options: list[tuple[float, float]] = []
    delivery_options: list[tuple[float, float]] = []
    source_options: list[tuple[float, float]] = []
    for candidate, text in zip(candidates, texts):
        score = float(candidate.get("score") or 0)
        for value in document_candidates(text, replacements):
            if value not in docs:
                docs.append(value)
        in_qty, delivery = station_weight(text)
        if in_qty is not None:
            station_options.append((in_qty, score))
        if delivery is not None:
            delivery_options.append((delivery, score))
        source = source_weight(text)
        if source is not None:
            source_options.append((source, score))
    in_qty = consensus(station_options)
    delivery = consensus(delivery_options)
    out_qty = consensus(source_options) or delivery
    material_name, spec, material_note = material(joined, list(config.get("material_rules") or []))
    notes = []
    if not docs:
        notes.append("待核：单据编号未识别")
    if material_note:
        notes.append(material_note)
    if in_qty is None:
        notes.append("待核：到场净重未确认")
    if out_qty is None:
        notes.append("待核：出场净重未确认")
    doc = docs[0] if docs else "待核"
    return {
        "source_file": Path(item.get("path") or "").name,
        "date": infer_date(joined, folder_date(folder)),
        "material": material_name,
        "spec": spec,
        "out_qty": out_qty,
        "in_qty": in_qty,
        "doc_no": doc,
        "tail_no": doc[-3:] if doc != "待核" else "",
        "car_no": plate(joined),
        "site": station(joined, str(config.get("default_site") or "待核")),
        "supplier": supplier(joined, list(config.get("supplier_patterns") or [])),
        "note": "；".join(dict.fromkeys(notes)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr-jsonl", required=True, type=Path)
    parser.add_argument("--photo-folder", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    rows = [parse_record(json.loads(line), args.photo_folder, config) for line in args.ocr_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda row: (row["doc_no"] == "待核", row["doc_no"], row["source_file"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "pending": sum("待核" in json.dumps(row, ensure_ascii=False) for row in rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
